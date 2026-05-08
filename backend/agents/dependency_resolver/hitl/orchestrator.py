"""
HITL WebSocket Orchestrator.

Manages live sessions: receives user messages, runs the solver pipeline,
streams LLM explanations, handles web search, enforces guardrails,
and gates the final lockfile behind an explicit APPROVE decision.
"""
from __future__ import annotations
import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Optional

from fastapi import WebSocket, WebSocketDisconnect

from agents.dependency_resolver.schemas import (
    ChatMessage, MessageType, SessionStatus,
    ApprovalRequest, ApprovalResponse, WSMessage,
    CreateSessionRequest, CreateSessionResponse,
    ResolveResponse,
)
from agents.dependency_resolver.hitl import session as session_store
from agents.dependency_resolver.hitl.guardrails import GuardrailLayer
from agents.dependency_resolver.hitl.search_tool import SearchTool
from agents.dependency_resolver.hitl.stream import stream_to_ws
from agents.dependency_resolver.hitl import approval_gateway as gw
from agents.dependency_resolver.llm.explainer import DependencyExplainer

logger = logging.getLogger(__name__)


class HITLOrchestrator:
    def __init__(self):
        self._connections: Dict[str, WebSocket] = {}
        self._pipeline_locks: Dict[str, asyncio.Lock] = {}
        self._guardrails  = GuardrailLayer()
        self._search      = SearchTool()
        self._explainer   = DependencyExplainer()

    # ── Session management ────────────────────────────────────────────────────

    async def create_session(self, req: CreateSessionRequest, base_url: str = "") -> CreateSessionResponse:
        sid = str(uuid.uuid4())
        session_store.create_session(
            session_id=sid,
            ecosystem=req.ecosystem,
            manifest=req.manifest,
            strategy=req.strategy,
            user_id=req.user_id,
        )
        ws_url = f"{base_url}/api/dependency_resolver/chat/{sid}"
        return CreateSessionResponse(
            session_id=sid,
            websocket_url=ws_url,
        )

    async def get_session_data(self, session_id: str):
        session = session_store.get_session(session_id)
        if not session:
            return None
        return session

    async def close_session(self, session_id: str):
        session = session_store.get_session(session_id)
        if session:
            session.status = SessionStatus.CLOSED
            session_store.save_session(session)
        ws = self._connections.pop(session_id, None)
        if ws:
            try:
                await ws.close()
            except Exception:
                pass
        return {"status": "closed"}

    # ── WebSocket lifecycle ───────────────────────────────────────────────────

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self._connections[session_id] = websocket
        session = session_store.get_session(session_id)
        if not session:
            await self._send(websocket, MessageType.ERROR, session_id,
                             {"text": f"Session {session_id} not found."})
            await websocket.close()
            return
        session.status = SessionStatus.ACTIVE
        session_store.save_session(session)
        logger.info(f"WS connected: session={session_id}")

        # Replay history for reconnect
        for msg in session.messages:
            try:
                await websocket.send_text(msg.model_dump_json())
            except Exception:
                break

        # Auto-start the resolver pipeline on first connect
        if not session.messages:
            await self._emit(session_id, MessageType.SYSTEM,
                             {"text": "Session started. Running dependency resolver…"})
            asyncio.create_task(self._run_resolve_pipeline(session_id))

    async def disconnect(self, session_id: str):
        self._connections.pop(session_id, None)
        logger.info(f"WS disconnected: session={session_id}")

    # ── Message router ────────────────────────────────────────────────────────

    async def handle_message(self, session_id: str, raw: dict):
        session = session_store.get_session(session_id)
        if not session:
            return

        text = raw.get("payload", {}).get("text", raw.get("text", "")).strip()
        msg_type = raw.get("type", MessageType.USER_MESSAGE.value)

        # Handle approval response (special frame)
        if msg_type == MessageType.APPROVAL_RESPONSE.value:
            await self._handle_approval_response(session_id, raw.get("payload", {}))
            return

        if not text:
            return

        # Persist user message
        user_msg = ChatMessage(
            session_id=session_id,
            type=MessageType.USER_MESSAGE,
            payload={"text": text},
        )
        session_store.add_message(session, user_msg)

        # ── Guardrail check ───────────────────────────────────────────────────
        result = self._guardrails.check_input(session_id, text)
        if not result.passed:
            await self._emit(session_id, MessageType.AGENT_MESSAGE,
                             {"text": result.reason})
            return
        safe_text = result.sanitised or text

        # ── Intent routing ────────────────────────────────────────────────────
        lower = safe_text.lower()

        # Explicit search request: starts with "search <anything>", "look up",
        # "find info on", or contains CVE/changelog-specific triggers.
        _SEARCH_TRIGGERS = (
            "search ",          # bare "search X" — covers "search who is X", "search CVE-…"
            "search for ",
            "look up ",
            "lookup ",
            "find info on ",
            "look up cve",
            "search cve",
            "is there a cve",
            "find the changelog",
            "search pypi",
            "search npm",
        )
        is_explicit_search = any(
            lower.startswith(k) or (k.strip() and f" {k}" in lower)
            for k in _SEARCH_TRIGGERS
        )

        _RERUN_TRIGGERS = (
            "/run", "/resolve", "/rerun",
            "re-run", "rerun", "retry", "resolve again", "restart resolver",
            "run again", "run pipeline", "run the pipeline", "run resolver",
            "run it", "run it again", "kick off", "start over", "start again",
            "do it", "do it again", "let's go", "lets go", "go again",
            "resolve it", "resolve now", "resolve please",
        )
        is_rerun = any(k in lower for k in _RERUN_TRIGGERS) or lower in ("run", "resolve", "go")

        # Detect a fresh manifest pasted into chat — if found, replace
        # the session's manifest and trigger a re-run automatically.
        new_manifest, detected_eco = self._detect_manifest(safe_text)

        if is_explicit_search:
            # Strip leading trigger verb so the query is clean
            query = safe_text
            for trigger in ("search for ", "search ", "look up ", "lookup ", "find info on "):
                if lower.startswith(trigger):
                    query = safe_text[len(trigger):].strip()
                    break
            await self._run_search(session_id, query)
        elif new_manifest:
            session.manifest = new_manifest
            if detected_eco:
                session.ecosystem = detected_eco  # type: ignore[assignment]
            session_store.save_session(session)
            await self._emit(session_id, MessageType.SYSTEM, {
                "text": (
                    f"New manifest detected ({detected_eco or session.ecosystem}). "
                    "Re-running resolver."
                ),
            })
            await self._run_resolve_pipeline(session_id)
        elif is_rerun:
            await self._emit(session_id, MessageType.SYSTEM,
                             {"text": "Re-running resolver pipeline."})
            await self._run_resolve_pipeline(session_id)
        else:
            # Default: conversational answer with full session context.
            # After the LLM responds, check if it wants to trigger a search
            # (it may reply with "Let me search for that" — intercept that here).
            await self._answer_question(session_id, safe_text)

    # ── Manifest detection ────────────────────────────────────────────────────

    @staticmethod
    def _detect_manifest(text: str) -> tuple[Optional[str], Optional[str]]:
        """
        Detect whether the user pasted a dependency manifest in chat.
        Returns (manifest_text, ecosystem) or (None, None).

        Manifest must look substantial — short messages with a single
        version specifier are not treated as manifests (likely chat).
        """
        import re
        stripped = text.strip()
        if len(stripped) < 12:
            return None, None

        # package.json — JSON object with "dependencies" key
        if stripped.startswith("{") and '"dependencies"' in stripped:
            try:
                obj = json.loads(stripped)
                if isinstance(obj.get("dependencies"), dict) or isinstance(obj.get("devDependencies"), dict):
                    return stripped, "npm"
            except (json.JSONDecodeError, ValueError):
                pass

        # Cargo.toml — has [dependencies] section
        if "[dependencies]" in stripped and "=" in stripped:
            return stripped, "cargo"

        # pom.xml — Maven
        if "<dependency>" in stripped and "<groupId>" in stripped:
            return stripped, "maven"

        # requirements.txt — multi-line with version specifiers
        # Require at least 2 lines that look like requirements to avoid
        # matching one-off mentions like "I want flask>=2.0 in my project"
        lines = [l.strip() for l in stripped.splitlines() if l.strip() and not l.strip().startswith("#")]
        req_pattern = re.compile(r"^[a-zA-Z0-9_\-.]+\s*([><=~!]=?|@)\s*\S+")
        req_lines = [l for l in lines if req_pattern.match(l)]
        if len(req_lines) >= 2:
            return "\n".join(req_lines), "pypi"

        return None, None

    # ── Resolver pipeline (runs async, emits events) ──────────────────────────

    async def _run_resolve_pipeline(self, session_id: str):
        lock = self._pipeline_locks.setdefault(session_id, asyncio.Lock())
        if lock.locked():
            await self._emit(session_id, MessageType.AGENT_MESSAGE,
                             {"text": "A resolution is already running. Please wait."})
            return
        async with lock:
            await self._run_resolve_pipeline_inner(session_id)

    async def _run_resolve_pipeline_inner(self, session_id: str):
        session = session_store.get_session(session_id)
        if not session:
            return

        trace_id = str(uuid.uuid4())
        session.trace_ids.append(trace_id)

        try:
            # Import here to avoid circular at module load
            from agents.dependency_resolver.parsers import get_parser
            from agents.dependency_resolver.resolver.graph import DependencyGraph
            from agents.dependency_resolver.resolver.solver import PubGrubSolver
            from agents.dependency_resolver.resolver.conflicts import ConflictSet
            from agents.dependency_resolver.security.osv_client import OSVClient
            from agents.dependency_resolver.security.license_check import LicenseChecker

            # Stage 1 — Parse
            await self._emit(session_id, MessageType.SOLVER_EVENT,
                             {"stage": "parsing", "text": "Parsing manifest…"})
            parser = get_parser(session.ecosystem)
            direct = parser.parse(session.manifest)
            await self._emit(session_id, MessageType.SOLVER_EVENT,
                             {"stage": "parsing_done",
                              "text": f"Parsed {len(direct)} direct dependencies."})

            # Generate a short title for the conversation (LLM-driven, with
            # fallback to a manifest-derived label). Emitted once per session.
            if not session.title:
                try:
                    title = await self._explainer.generate_title(
                        manifest=session.manifest,
                        ecosystem=session.ecosystem,
                    )
                    session.title = title
                    session_store.save_session(session)
                    await self._emit(session_id, MessageType.SYSTEM, {
                        "kind": "title",
                        "title": title,
                        "text": f"Conversation titled: {title}",
                    })
                except Exception as exc:
                    logger.warning(f"title generation failed session={session_id}: {exc}")

            # Stage 2 — Build DAG
            await self._emit(session_id, MessageType.SOLVER_EVENT,
                             {"stage": "fetching",
                              "text": f"Fetching metadata for {len(direct)} packages…"})
            graph = DependencyGraph(session.ecosystem)
            await graph.build(direct)
            graph_dict = graph.to_dict()
            await self._emit(session_id, MessageType.SOLVER_EVENT,
                             {"stage": "fetching_done",
                              "text": f"Graph built: {len(graph_dict)} total packages."})

            # Stage 3 — Solve
            await self._emit(session_id, MessageType.SOLVER_EVENT,
                             {"stage": "solving", "text": "Running version solver…"})
            solver = PubGrubSolver(session.ecosystem, strategy=session.strategy)
            resolved, conflicts = await solver.solve(graph_dict)
            await self._emit(session_id, MessageType.SOLVER_EVENT,
                             {"stage": "solving_done",
                              "text": (
                                  f"Solver complete: {len(resolved)} resolved, "
                                  f"{len(conflicts)} conflict(s)."
                              )})

            # Stage 4 — Audit (CVE)
            await self._emit(session_id, MessageType.SOLVER_EVENT,
                             {"stage": "auditing", "text": "Auditing for vulnerabilities…"})
            osv = OSVClient()
            pkg_dicts = [p.model_dump() for p in resolved]
            annotated = await osv.annotate_packages(pkg_dicts, session.ecosystem)
            # Re-hydrate vulnerabilities into resolved list
            vuln_map = {p["name"]: p.get("vulnerabilities", []) for p in annotated}
            cve_count = 0
            for pkg in resolved:
                pkg.vulnerabilities = vuln_map.get(pkg.name, [])
                cve_count += len(pkg.vulnerabilities)
            await self._emit(session_id, MessageType.SOLVER_EVENT,
                             {"stage": "auditing_done",
                              "text": f"Audit done: {cve_count} CVE(s) found."})

            # Stage 4b — License check
            license_issues = LicenseChecker().check([p.model_dump() for p in resolved])

            # Stage 5 — LLM explanation (streamed)
            await self._emit(session_id, MessageType.SOLVER_EVENT,
                             {"stage": "explaining",
                              "text": "Generating conflict explanation…"})

            full_explanation = ""
            if conflicts:
                gen = self._explainer.stream_explanation(conflicts, resolved)
                async def emit_token(token: str, done: bool):
                    nonlocal full_explanation
                    full_explanation += token
                    await self._emit_stream(session_id, token, done)

                full_explanation = await stream_to_ws(gen, emit_token)
            else:
                msg = "No conflicts detected. All dependencies resolved cleanly."
                await self._emit(session_id, MessageType.AGENT_MESSAGE, {"text": msg})
                full_explanation = msg

            # Stage 6 — Build lockfile + report
            lockfile = self._explainer.build_lockfile(resolved, session.ecosystem)
            report   = self._explainer.build_report(
                resolved, conflicts, session.ecosystem,
                session.strategy, full_explanation,
                license_issues, lockfile,
            )

            # Stage 7 — Output guardrails
            report, warnings = self._guardrails.check_output(
                report,
                allowed_versions=[p.version for p in resolved],
            )
            if warnings:
                for w in warnings:
                    logger.warning(f"[session={session_id}] output guardrail: {w}")

            # Snapshot stats onto the session — survives approval / rejection
            session.resolution_stats = {
                "resolved":  len(resolved),
                "conflicts": len(conflicts),
                "cves":      cve_count,
                "licenses":  len(license_issues),
            }
            session_store.save_session(session)

            # Stage 8 — Build ResolveResponse and register approval
            response = ResolveResponse(
                ok=len(conflicts) == 0,
                resolved=resolved,
                conflicts=conflicts,
                lockfile=lockfile,
                report_markdown=report,
                trace_id=trace_id,
            )
            approval = ApprovalRequest(
                session_id=session_id,
                proposed_lockfile=lockfile,
                report_markdown=report,
                conflicts=conflicts,
                stats={
                    "resolved": len(resolved),
                    "conflicts": len(conflicts),
                    "cves": cve_count,
                    "license_issues": len(license_issues),
                },
            )
            gw.store_result(session_id, response)
            gw.register(approval)

            session.status = SessionStatus.PENDING_APPROVAL
            session.pending_approval = approval
            session_store.save_session(session)

            await self._emit(session_id, MessageType.APPROVAL_REQUEST,
                             approval.model_dump())

        except Exception as exc:
            logger.exception(f"Pipeline error session={session_id}: {exc}")
            await self._emit(session_id, MessageType.ERROR,
                             {"text": f"Resolution failed: {exc}"})

    # ── Conversational answer ─────────────────────────────────────────────────

    async def _answer_question(self, session_id: str, text: str):
        session = session_store.get_session(session_id)
        if not session:
            return

        history = session_store.get_history(session)

        # ── Read session stats (most reliable source is resolution_stats snapshot)
        stats = session.resolution_stats or {}
        # Fall back to pending_approval.stats if snapshot not yet written
        if not stats and session.pending_approval:
            stats = session.pending_approval.stats or {}
        resolved_count = stats.get("resolved", 0)
        conflict_count = stats.get("conflicts", 0)
        cve_count      = stats.get("cves", 0)

        # ── Build manifest_summary from first lines of manifest ───────────────
        manifest_lines = (session.manifest or "").strip().splitlines()
        preview_lines = [l for l in manifest_lines if l.strip() and not l.strip().startswith("#")][:5]
        manifest_summary = (
            f"{len(manifest_lines)} lines, first entries: "
            + ", ".join(preview_lines[:3])
            if preview_lines
            else "(manifest not yet provided)"
        )

        gen = self._explainer.stream_chat_response(
            user_message=text,
            history=history,
            ecosystem=session.ecosystem,
            strategy=session.strategy,
            resolved_count=resolved_count,
            conflict_count=conflict_count,
            cve_count=cve_count,
            manifest_summary=manifest_summary,
        )
        full = ""
        async def emit_token(token: str, done: bool):
            nonlocal full
            full += token
            await self._emit_stream(session_id, token, done)

        full = await stream_to_ws(gen, emit_token)

        # ── Intercept "Let me search for that" from LLM ───────────────────────
        # If the LLM signals it wants to search (instead of answering from context),
        # automatically trigger a real web search rather than leaving the user
        # in an infinite loop of "Let me search for that" with no action.
        _SEARCH_SIGNAL_PHRASES = (
            "let me search for that",
            "let me search for",
            "i'll search for",
            "i will search for",
            "searching for that",
            "let me look that up",
            "i'll look that up",
        )
        full_lower = full.lower()
        wants_search = any(phrase in full_lower for phrase in _SEARCH_SIGNAL_PHRASES)
        if wants_search:
            # Persist the LLM's "I'll search…" stub so conversation is coherent
            session_store.add_message(session, ChatMessage(
                session_id=session_id,
                type=MessageType.AGENT_MESSAGE,
                payload={"text": full},
            ))
            # Build a focused search query instead of passing raw user text
            clean_query = await self._explainer.build_search_query(
                user_question=text,
                manifest_summary=manifest_summary,
                ecosystem=session.ecosystem,
            )
            await self._run_search(session_id, clean_query)
            return

        # Persist agent message
        agent_msg = ChatMessage(
            session_id=session_id,
            type=MessageType.AGENT_MESSAGE,
            payload={"text": full},
        )
        session_store.add_message(session, agent_msg)

    # ── Web search ────────────────────────────────────────────────────────────

    async def _run_search(self, session_id: str, query: str):
        # Rate-limit check
        rate_ok = self._guardrails.check_search_rate(session_id)
        if not rate_ok.passed:
            await self._emit(session_id, MessageType.AGENT_MESSAGE,
                             {"text": rate_ok.reason})
            return

        # Announce search before executing
        await self._emit(session_id, MessageType.SEARCH_EVENT, {
            "stage": "announced",
            "query": query,
            "text": f"Searching for: {query}",
        })

        results = await self._search.search(query)

        if not results:
            await self._emit(session_id, MessageType.SEARCH_EVENT, {
                "stage": "no_results",
                "text": "No results found on allow-listed domains.",
            })
            await self._emit(session_id, MessageType.AGENT_MESSAGE,
                             {"text": "I couldn't find relevant results for that query "
                                      "on the allow-listed sources."})
            return

        await self._emit(session_id, MessageType.SEARCH_EVENT, {
            "stage": "results",
            "results": [r.model_dump() for r in results],
            "text": f"Found {len(results)} result(s).",
        })

        # Synthesise answer from results
        gen = self._explainer.synthesise_search(
            question=query,
            search_results=[r.model_dump() for r in results],
        )
        full = ""
        async def emit_token(token: str, done: bool):
            nonlocal full
            full += token
            await self._emit_stream(session_id, token, done)

        full = await stream_to_ws(gen, emit_token)

        session = session_store.get_session(session_id)
        if session:
            session_store.add_message(session, ChatMessage(
                session_id=session_id,
                type=MessageType.AGENT_MESSAGE,
                payload={"text": full, "search_citations": [r.model_dump() for r in results]},
            ))

    # ── Approval handling ─────────────────────────────────────────────────────

    async def _handle_approval_response(self, session_id: str, payload: dict):
        session = session_store.get_session(session_id)
        if not session or not session.pending_approval:
            await self._emit(session_id, MessageType.ERROR,
                             {"text": "No pending approval found for this session."})
            return

        decision = payload.get("decision", "").upper()
        if decision not in ("APPROVE", "REJECT"):
            await self._emit(session_id, MessageType.ERROR,
                             {"text": "Decision must be APPROVE or REJECT."})
            return

        response = ApprovalResponse(
            approval_id=session.pending_approval.approval_id,
            session_id=session_id,
            decision=decision,  # type: ignore[arg-type]
            comment=payload.get("comment"),
        )
        final_result = gw.decide(response)

        if decision == "APPROVE":
            session.status = SessionStatus.APPROVED
            session_store.save_session(session)
            await self._emit(session_id, MessageType.SYSTEM, {
                "text": "Approved. Lockfile finalised.",
                "lockfile": final_result.lockfile if final_result else "",
                "report_markdown": final_result.report_markdown if final_result else "",
            })
        else:
            session.status = SessionStatus.REJECTED
            session.pending_approval = None
            session_store.save_session(session)
            comment = payload.get("comment", "No reason given.")
            await self._emit(session_id, MessageType.SYSTEM, {
                "text": f"Rejected. Reason: {comment}. "
                        "You can ask follow-up questions or request a re-run.",
            })

    # ── REST approval fallback ────────────────────────────────────────────────

    async def handle_rest_approval(self, session_id: str, payload: ApprovalResponse):
        return await self._handle_approval_response(session_id, payload.model_dump())

    # ── Emit helpers ──────────────────────────────────────────────────────────

    async def _emit(self, session_id: str, msg_type: MessageType, payload: dict):
        ws = self._connections.get(session_id)
        frame = WSMessage(
            type=msg_type,
            session_id=session_id,
            payload=payload,
            done=True,
        )
        if ws:
            try:
                await ws.send_text(frame.model_dump_json())
            except Exception as exc:
                logger.warning(f"emit error session={session_id}: {exc}")

        # Persist solver events and system messages so _answer_question
        # can read stats from session.messages even after WS reconnect.
        _PERSIST_TYPES = {
            MessageType.SOLVER_EVENT,
            MessageType.SYSTEM,
            MessageType.APPROVAL_REQUEST,
        }
        if msg_type in _PERSIST_TYPES:
            session = session_store.get_session(session_id)
            if session:
                session_store.add_message(session, ChatMessage(
                    session_id=session_id,
                    type=msg_type,
                    payload=payload,
                ))

    async def _emit_stream(self, session_id: str, token: str, done: bool):
        ws = self._connections.get(session_id)
        if not ws:
            return
        frame = WSMessage(
            type=MessageType.AGENT_MESSAGE,
            session_id=session_id,
            payload={"delta": token},
            done=done,
        )
        try:
            await ws.send_text(frame.model_dump_json())
        except Exception:
            pass

    async def _send(self, ws: WebSocket, msg_type: MessageType,
                    session_id: str, payload: dict):
        frame = WSMessage(type=msg_type, session_id=session_id, payload=payload)
        try:
            await ws.send_text(frame.model_dump_json())
        except Exception:
            pass

    # ── Health ────────────────────────────────────────────────────────────────

    async def health_check(self) -> dict:
        from agents.dependency_resolver.hitl.search_tool import _PROVIDER
        return {
            "status": "healthy",
            "active_sessions": len(self._connections),
            "search_provider": _PROVIDER,
        }
