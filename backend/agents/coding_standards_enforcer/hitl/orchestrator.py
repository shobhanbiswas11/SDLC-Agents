"""
HITL WebSocket orchestrator for the Coding Standards Enforcer.

Manages live chat sessions: receives user messages, runs analyze / polish
pipelines, streams LLM answers, and gates "apply this fix" actions behind
an explicit APPROVE decision.

Frame format on the wire (both directions):
    {
        "type": "<MessageType>",
        "session_id": "...",
        "message_id": "...",
        "timestamp": "ISO8601",
        "payload": {...},
        "done": true|false,
    }
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Dict, Optional

from fastapi import WebSocket

from agents.coding_standards_enforcer.agent import (
    analyze_code,
    fix_all_violations,
    generate_diff,
    polish_code,
)
from agents.coding_standards_enforcer.hitl import (
    approval_gateway as gw,
    session_store,
)
from agents.coding_standards_enforcer.hitl.guardrails import GuardrailLayer
from agents.coding_standards_enforcer.schemas import (
    ApprovalResponse,
    ChatMessage,
    CreateSessionRequest,
    CreateSessionResponse,
    MessageType,
    SessionStatus,
    WSMessage,
)
from core.services.llm_service import get_llm

logger = logging.getLogger(__name__)


# Words/phrases that mean "yes, apply" without going through the formal
# approval frame — convenience for chat-style replies.
_APPROVE_TOKENS = {
    "approve",
    "yes",
    "y",
    "apply",
    "go ahead",
    "do it",
    "fix it",
    "looks good",
    "lgtm",
}
_REJECT_TOKENS = {"reject", "no", "n", "abort", "cancel", "stop"}

# Trigger phrases for kicking off a polish run from chat.
_POLISH_TOKENS = {
    "polish",
    "fix all",
    "fix it",
    "clean up",
    "make it clean",
    "apply the fixes",
}


class HITLOrchestrator:
    def __init__(self) -> None:
        self._connections: Dict[str, WebSocket] = {}
        self._pipeline_locks: Dict[str, asyncio.Lock] = {}
        self._guardrails = GuardrailLayer()

    # ── Session management ────────────────────────────────────

    async def create_session(
        self, req: CreateSessionRequest, base_url: str = ""
    ) -> CreateSessionResponse:
        sid = str(uuid.uuid4())
        session_store.create_session(
            session_id=sid,
            code=req.code,
            language=req.language,
            user_id=req.user_id,
            title=req.title,
        )
        ws_url = f"{base_url}/api/coding_standards_enforcer/chat/{sid}"
        return CreateSessionResponse(session_id=sid, websocket_url=ws_url)

    async def get_session_data(self, session_id: str):
        return session_store.get_session(session_id)

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

    # ── WebSocket lifecycle ───────────────────────────────────

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        await websocket.accept()
        self._connections[session_id] = websocket

        session = session_store.get_session(session_id)
        if not session:
            await self._send(
                websocket,
                MessageType.ERROR,
                session_id,
                {"text": f"Session {session_id} not found."},
            )
            await websocket.close()
            return

        session.status = SessionStatus.ACTIVE
        session_store.save_session(session)
        logger.info("WS connected: session=%s", session_id)

        # Replay history for reconnects.
        for msg in session.messages:
            try:
                await websocket.send_text(msg.model_dump_json())
            except Exception:
                break

        # First connect → introduce ourselves and run an initial analysis.
        if not session.messages:
            await self._emit(
                session_id,
                MessageType.SYSTEM,
                {
                    "text": (
                        "I'm the Coding Standards assistant. I've loaded your "
                        f"{session.language} code — analysing it now…"
                    )
                },
            )
            asyncio.create_task(self._run_initial_analysis(session_id))

    async def disconnect(self, session_id: str) -> None:
        self._connections.pop(session_id, None)
        logger.info("WS disconnected: session=%s", session_id)

    # ── Inbound message router ────────────────────────────────

    async def handle_message(self, session_id: str, raw: dict) -> None:
        session = session_store.get_session(session_id)
        if not session:
            return

        msg_type = raw.get("type", MessageType.USER_MESSAGE.value)

        # Approval response — special-case so we don't run the LLM.
        if msg_type == MessageType.APPROVAL_RESPONSE.value:
            await self._handle_approval_response(session_id, raw.get("payload", {}))
            return

        text = raw.get("payload", {}).get("text", raw.get("text", ""))
        guard = self._guardrails.check_user_message(text)
        if not guard.ok:
            await self._emit(
                session_id,
                MessageType.SYSTEM,
                {"text": guard.reason or "I couldn't process that message."},
            )
            return

        # Persist the user message into the session history so it replays on
        # reconnect — but do NOT emit it back over the WS, because the client
        # already echoed it locally. Otherwise the bubble shows twice.
        self._store(session_id, MessageType.USER_MESSAGE, {"text": guard.text})

        lower = guard.text.lower()
        if any(tok in lower for tok in _POLISH_TOKENS):
            asyncio.create_task(self._run_polish(session_id))
            return

        # Plain chat → conversational answer.
        asyncio.create_task(self._answer_question(session_id, guard.text))

    # ── Pipelines ─────────────────────────────────────────────

    async def _run_initial_analysis(self, session_id: str) -> None:
        async with self._lock(session_id):
            session = session_store.get_session(session_id)
            if not session:
                return

            await self._emit(
                session_id,
                MessageType.ANALYZE_EVENT,
                {"stage": "analyze", "text": "Analysing for violations…"},
            )

            # analyze_code is sync; run it off the loop so we don't block.
            result = await asyncio.to_thread(
                analyze_code, session.code, session.language
            )
            violations = result.get("violations", []) or []
            summary = result.get("summary", {}) or {}

            await self._emit(
                session_id,
                MessageType.ANALYZE_EVENT,
                {
                    "stage": "analyze_done",
                    "violations": violations,
                    "summary": summary,
                    "text": f"Found {len(violations)} violation(s).",
                },
            )

            if violations:
                preview_lines = [
                    f"- L{v.get('line', '?')} [{v.get('rule_code', '')}] {v.get('message', '')}"
                    for v in violations[:5]
                ]
                more = (
                    f"\n…and {len(violations) - 5} more"
                    if len(violations) > 5
                    else ""
                )
                msg = (
                    f"I found **{len(violations)}** issue(s):\n\n"
                    + "\n".join(preview_lines)
                    + more
                    + "\n\nReply **fix all** and I'll polish the code, "
                    "or ask me about a specific violation."
                )
            else:
                msg = "Your code already looks clean — no violations detected."

            await self._record(session_id, MessageType.AGENT_MESSAGE, {"text": msg})

    async def _run_polish(self, session_id: str) -> None:
        async with self._lock(session_id):
            session = session_store.get_session(session_id)
            if not session:
                return

            await self._emit(
                session_id,
                MessageType.POLISH_EVENT,
                {"stage": "polish", "text": "Polishing the code…"},
            )

            result = await asyncio.to_thread(
                polish_code, session.code, session.language, 5
            )
            polished = result.get("fixed_code", session.code)
            remaining = result.get("remaining_violations", []) or []
            diff = result.get("diff", "")

            session.last_polished_code = polished
            session_store.save_session(session)

            await self._emit(
                session_id,
                MessageType.POLISH_EVENT,
                {
                    "stage": "polish_done",
                    "passes_used": result.get("passes_used", 0),
                    "remaining_violations": remaining,
                    "text": (
                        f"Polish finished after {result.get('passes_used', 0)} "
                        f"pass(es). {len(remaining)} violation(s) remain."
                    ),
                },
            )

            # Build the approval card.
            approval = gw.build_approval_request(
                session_id=session_id,
                proposed_code=polished,
                diff=diff,
                summary=(
                    f"Polished code with {len(remaining)} remaining violation(s)."
                ),
                remaining_violations=remaining,
            )
            session.pending_approval = approval
            session.status = SessionStatus.PENDING_APPROVAL
            session_store.save_session(session)

            await self._emit(
                session_id,
                MessageType.APPROVAL_REQUEST,
                approval.model_dump(mode="json"),
            )

            await self._record(
                session_id,
                MessageType.AGENT_MESSAGE,
                {
                    "text": (
                        "Here's the polished version. Reply **approve** to "
                        "apply it, or **reject** to discard."
                    )
                },
            )

    async def _answer_question(self, session_id: str, text: str) -> None:
        """Plain chat — conversational LLM response with code context."""
        async with self._lock(session_id):
            session = session_store.get_session(session_id)
            if not session:
                return

            try:
                llm = get_llm()
            except Exception as exc:
                await self._record(
                    session_id,
                    MessageType.AGENT_MESSAGE,
                    {
                        "text": (
                            "I can't reach the LLM right now: "
                            f"{exc}. The analyze and polish features still work."
                        )
                    },
                )
                return

            # Cheap, capped context window — last 6 user/assistant turns.
            history = session_store.get_history(session)[-6:]
            history_text = "\n".join(
                f"{m['role']}: {m['content']}" for m in history
            )

            prompt = (
                "You are an assistant that helps developers understand and "
                "fix coding-standard violations. Answer in 1-3 short "
                "paragraphs. Refer to specific line numbers and rule codes "
                "when helpful. If the user asks for a fix, suggest a small "
                "concrete change rather than re-writing the whole file.\n\n"
                f"Language: {session.language}\n\n"
                f"--- Current code ---\n{session.code}\n--- end ---\n\n"
                f"Recent conversation:\n{history_text}\n\n"
                f"User: {text}\nAssistant:"
            )

            try:
                response = await asyncio.to_thread(llm.invoke, prompt)
                content = (
                    response.content
                    if hasattr(response, "content")
                    else str(response)
                ).strip()
            except Exception as exc:
                content = f"LLM error: {exc}"

            await self._record(
                session_id, MessageType.AGENT_MESSAGE, {"text": content}
            )

    # ── Approval handling ─────────────────────────────────────

    async def _handle_approval_response(
        self, session_id: str, payload: dict
    ) -> None:
        session = session_store.get_session(session_id)
        if not session or not session.pending_approval:
            await self._emit(
                session_id,
                MessageType.SYSTEM,
                {"text": "There's no fix awaiting approval right now."},
            )
            return

        decision = payload.get("decision", "REJECT").upper()
        if decision == "APPROVE":
            session.code = session.last_polished_code or session.code
            session.pending_approval = None
            session.status = SessionStatus.ACTIVE
            session_store.save_session(session)
            await self._record(
                session_id,
                MessageType.SYSTEM,
                {
                    "text": "Applied the polished code to the session.",
                    "kind": "fix_applied",
                    "code": session.code,
                },
            )
        else:
            session.pending_approval = None
            session.status = SessionStatus.ACTIVE
            session_store.save_session(session)
            await self._record(
                session_id,
                MessageType.SYSTEM,
                {"text": "Rejected the polished code — keeping the original."},
            )

    async def handle_rest_approval(
        self, session_id: str, payload: ApprovalResponse
    ) -> dict:
        await self._handle_approval_response(
            session_id,
            {"decision": payload.decision, "comment": payload.comment},
        )
        return {"status": "ok"}

    # ── Internal helpers ──────────────────────────────────────

    def _lock(self, session_id: str) -> asyncio.Lock:
        lock = self._pipeline_locks.get(session_id)
        if lock is None:
            lock = asyncio.Lock()
            self._pipeline_locks[session_id] = lock
        return lock

    async def _emit(
        self, session_id: str, msg_type: MessageType, payload: dict
    ) -> None:
        ws = self._connections.get(session_id)
        if ws is None:
            return
        try:
            await self._send(ws, msg_type, session_id, payload)
        except Exception as exc:
            logger.warning("Could not send to %s: %s", session_id, exc)

    async def _record(
        self, session_id: str, msg_type: MessageType, payload: dict
    ) -> None:
        """Emit a frame AND store it in the session history."""
        session = session_store.get_session(session_id)
        if not session:
            return
        msg = ChatMessage(session_id=session_id, type=msg_type, payload=payload)
        session_store.add_message(session, msg)
        await self._emit(session_id, msg_type, payload)

    def _store(
        self, session_id: str, msg_type: MessageType, payload: dict
    ) -> None:
        """Persist a frame into the session history WITHOUT emitting it.

        Used for user_message frames: the client already shows the bubble
        locally, so re-emitting would double-render it. Reconnect replay
        still works because the message lands in session.messages.
        """
        session = session_store.get_session(session_id)
        if not session:
            return
        msg = ChatMessage(session_id=session_id, type=msg_type, payload=payload)
        session_store.add_message(session, msg)

    @staticmethod
    async def _send(
        websocket: WebSocket,
        msg_type: MessageType,
        session_id: str,
        payload: dict,
    ) -> None:
        frame = WSMessage(
            type=msg_type, session_id=session_id, payload=payload
        )
        await websocket.send_text(frame.model_dump_json())

    async def health_check(self) -> dict:
        return {
            "active_sessions": len(self._connections),
            "tracked_sessions": len(self._pipeline_locks),
        }
