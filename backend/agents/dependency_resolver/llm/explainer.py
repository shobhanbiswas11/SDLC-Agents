"""
LLM-driven explanation layer.
Wraps core LLMService (Azure AD auth). Never picks versions — only explains.
"""
from __future__ import annotations
import json
import logging
from typing import AsyncIterator, List

from agents.dependency_resolver.schemas import Conflict, ResolvedPackage
from agents.dependency_resolver.llm.prompts import (
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_TEMPLATE,
    CONFLICT_EXPLAIN_TEMPLATE,
    CHAT_CONTEXT_TEMPLATE,
    SEARCH_SYNTHESIS_TEMPLATE,
    REPORT_TEMPLATE,
)
from core.llm import get_llm_service

logger = logging.getLogger(__name__)


def _msg(role: str, content: str) -> dict:
    return {"role": role, "content": content}


def _system_msg(
    ecosystem: str = "pypi",
    strategy: str = "stable",
    resolved_count: int = 0,
    conflict_count: int = 0,
    cve_count: int = 0,
    manifest_summary: str = "(not yet resolved)",
) -> dict:
    """Build the session-aware system message."""
    content = SYSTEM_PROMPT_TEMPLATE.format(
        ecosystem=ecosystem,
        strategy=strategy,
        resolved_count=resolved_count,
        conflict_count=conflict_count,
        cve_count=cve_count,
        manifest_summary=manifest_summary,
    )
    return _msg("system", content)


class DependencyExplainer:
    def __init__(self):
        self._svc = get_llm_service()

    def _available(self) -> bool:
        return self._svc.available()

    # ── Conflict explanation (streaming) ─────────────────────────────────────

    async def stream_explanation(
        self,
        conflicts: List[Conflict],
        resolved: List[ResolvedPackage],
        ecosystem: str = "pypi",
        strategy: str = "stable",
    ) -> AsyncIterator[str]:
        if not conflicts:
            yield "No conflicts. All packages resolved cleanly."
            return
        if not self._available():
            yield self._fallback_explanation(conflicts)
            return

        conflicts_json = json.dumps(
            [c.model_dump(exclude_none=True) for c in conflicts], indent=2
        )
        resolved_json = json.dumps(
            [{"name": r.name, "version": r.version} for r in resolved], indent=2
        )
        manifest_summary = f"{len(resolved)} packages resolved, {len(conflicts)} conflict(s)"

        messages = [
            _system_msg(
                ecosystem=ecosystem,
                strategy=strategy,
                resolved_count=len(resolved),
                conflict_count=len(conflicts),
                manifest_summary=manifest_summary,
            ),
            _msg("user", CONFLICT_EXPLAIN_TEMPLATE.format(
                conflicts_json=conflicts_json,
                resolved_json=resolved_json,
            )),
        ]
        async for token in self._svc.astream_messages(messages):
            if token:
                yield token

    # ── Conversational chat (streaming) ──────────────────────────────────────

    async def stream_chat_response(
        self,
        user_message: str,
        history: List[dict],
        ecosystem: str,
        strategy: str,
        resolved_count: int,
        conflict_count: int,
        cve_count: int,
        manifest_summary: str = "",
    ) -> AsyncIterator[str]:
        if not self._available():
            yield (
                "The LLM is not configured yet. "
                "Set AZURE_TENANT_ID / AZURE_CLIENT_ID / AZURE_CLIENT_SECRET in backend/.env "
                "and restart the server."
            )
            return

        # Build conversation history string.
        # Always pin the first message so the LLM never forgets what started the
        # session; then include the most recent 20 turns.
        _WINDOW = 20
        history_lines: list = []

        def _fmt(m: dict):
            role = "Engineer" if m["role"] == "user" else "Agent"
            content = (m.get("content") or "").strip()
            return f"{role}: {content}" if content else None

        if history:
            recent = history[-_WINDOW:]
            first_fmt = _fmt(history[0])
            # Only pin first message if it isn't already inside the window
            if first_fmt and history[0] not in recent:
                history_lines.append(first_fmt)
                history_lines.append("... [earlier messages omitted] ...")
            for m in recent:
                line = _fmt(m)
                if line:
                    history_lines.append(line)

        history_text = "\n".join(history_lines) if history_lines else "(This is the start of the conversation)"

        messages = [
            _system_msg(
                ecosystem=ecosystem,
                strategy=strategy,
                resolved_count=resolved_count,
                conflict_count=conflict_count,
                cve_count=cve_count,
                manifest_summary=manifest_summary or f"{resolved_count} packages in scope",
            ),
            _msg("user", CHAT_CONTEXT_TEMPLATE.format(
                history=history_text,
                user_message=user_message,
            )),
        ]
        async for token in self._svc.astream_messages(messages):
            if token:
                yield token

    # ── Search query builder (non-streaming) ────────────────────────────────
    async def build_search_query(
        self,
        user_question: str,
        manifest_summary: str = "",
        ecosystem: str = "pypi",
    ) -> str:
        """
        Ask the LLM to rewrite the user's question as a focused web-search
        query (≤10 words, no filler, actionable for osv.dev / nvd / PyPI).
        Falls back to a simple cleaned-up version of the original if LLM is
        unavailable.
        """
        if not self._available():
            # Best-effort heuristic: strip question words, keep nouns
            import re
            q = re.sub(
                r"\b(what|are|the|is|there|any|a|an|for|of|in|do|does|can|"
                r"you|tell|me|about|potential|please|give|show)\b",
                "", user_question, flags=re.IGNORECASE,
            ).strip()
            return q or user_question

        prompt = (
            f"Rewrite the following question as a concise web-search query "
            f"(max 10 words, no question marks, no filler words). "
            f"Context: {ecosystem} ecosystem. Manifest: {manifest_summary}.\n\n"
            f"Question: {user_question}\n\nSearch query:"
        )
        messages = [
            _msg("system", "You produce short, focused web-search queries. Output only the query."),
            _msg("user", prompt),
        ]
        query_parts: list[str] = []
        async for token in self._svc.astream_messages(messages):
            if token:
                query_parts.append(token)
        result = "".join(query_parts).strip().strip('"').strip("'")
        return result or user_question

    # ── Chat title generation (non-streaming) ────────────────────────────────
    async def generate_title(
        self,
        manifest: str,
        ecosystem: str = "pypi",
    ) -> str:
        """
        Ask the LLM to produce a short (3-6 word) title summarising
        the resolution session. Returns a clean, capitalised title.
        Falls back to a derived title if LLM is unavailable.
        """
        # Always have a sensible fallback
        fallback = self._fallback_title(manifest, ecosystem)

        if not self._available():
            return fallback

        manifest_preview = manifest[:600]
        prompt = (
            f"Summarise this {ecosystem} dependency manifest as a short, descriptive "
            f"title (3 to 6 words, Title Case, no quotes, no trailing punctuation, "
            f"no emoji). Focus on the dominant frameworks or purpose.\n\n"
            f"Manifest:\n{manifest_preview}\n\nTitle:"
        )
        messages = [
            _msg("system", "You produce concise, descriptive titles. Output only the title."),
            _msg("user", prompt),
        ]
        try:
            parts: list[str] = []
            async for token in self._svc.astream_messages(messages):
                if token:
                    parts.append(token)
            result = "".join(parts).strip().strip('"').strip("'").strip(".")
            # Strip leading "Title:" if model echoes the prompt
            if result.lower().startswith("title:"):
                result = result[6:].strip()
            # Limit length
            words = result.split()
            if len(words) > 8:
                result = " ".join(words[:8])
            return result or fallback
        except Exception:
            return fallback

    @staticmethod
    def _fallback_title(manifest: str, ecosystem: str) -> str:
        import json as _json
        ECO_LABEL = {"pypi": "Python", "npm": "Node", "maven": "Java", "cargo": "Rust"}
        eco = ECO_LABEL.get(ecosystem, ecosystem.title())
        try:
            if ecosystem == "npm":
                obj = _json.loads(manifest)
                pkgs = list((obj.get("dependencies") or obj.get("devDependencies") or {}).keys())
                if pkgs:
                    return f"{eco}: " + ", ".join(pkgs[:2]).title()
        except Exception:
            pass
        lines = [
            l.strip() for l in manifest.splitlines()
            if l.strip()
            and not l.strip().startswith("#")
            and not l.strip().startswith("[")
            and not l.strip().startswith("<")
        ]
        names = []
        for l in lines[:5]:
            name = l.split("=")[0].split(">")[0].split("<")[0].split("~")[0].split("!")[0].strip().strip('"')
            if name and name.replace("-", "").replace("_", "").replace(".", "").isalnum():
                names.append(name)
            if len(names) >= 2:
                break
        if names:
            return f"{eco}: " + ", ".join(names[:2]).title()
        return f"{eco} Dependencies"

    # ── Search synthesis (streaming) ─────────────────────────────────────────

    async def synthesise_search(
        self, question: str, search_results: List[dict],
        ecosystem: str = "pypi",
    ) -> AsyncIterator[str]:
        if not self._available():
            yield "LLM not configured — cannot synthesise results."
            return

        results_text = "\n\n".join(
            f"[{i+1}] {r.get('title','')}\nURL: {r.get('url','')}\n{r.get('snippet','')}"
            for i, r in enumerate(search_results)
        )
        messages = [
            _system_msg(ecosystem=ecosystem),
            _msg("user", SEARCH_SYNTHESIS_TEMPLATE.format(
                question=question,
                search_results=results_text or "(no results)",
            )),
        ]
        async for token in self._svc.astream_messages(messages):
            if token:
                yield token

    # ── Lockfile builder ──────────────────────────────────────────────────────

    def build_lockfile(self, resolved: List[ResolvedPackage], ecosystem: str) -> str:
        if ecosystem == "pypi":
            return "# Generated by Dependency Resolver Agent\n" + "\n".join(
                f"{p.name}=={p.version}" for p in resolved
            )
        elif ecosystem == "npm":
            return json.dumps(
                {"dependencies": {p.name: p.version for p in resolved}}, indent=2
            )
        elif ecosystem == "maven":
            lines = ["<dependencies>"]
            for p in resolved:
                g, a = (p.name.split(":") + [p.name])[:2]
                lines.append(
                    f"  <dependency>\n"
                    f"    <groupId>{g}</groupId>\n"
                    f"    <artifactId>{a}</artifactId>\n"
                    f"    <version>{p.version}</version>\n"
                    f"  </dependency>"
                )
            lines.append("</dependencies>")
            return "\n".join(lines)
        elif ecosystem == "cargo":
            lines = []
            for p in resolved:
                lines.append(f'[dependencies.{p.name}]\nversion = "{p.version}"')
            return "\n\n".join(lines)
        return "\n".join(f"{p.name}=={p.version}" for p in resolved)

    # ── Report builder ────────────────────────────────────────────────────────

    def build_report(
        self,
        resolved: List[ResolvedPackage],
        conflicts: List[Conflict],
        ecosystem: str,
        strategy: str,
        conflict_explanation: str,
        license_issues: List[dict],
        lockfile: str,
    ) -> str:
        cve_count = sum(len(p.vulnerabilities) for p in resolved)
        security_lines = [
            f"- **{p.name}@{p.version}**: {cve}"
            for p in resolved for cve in p.vulnerabilities
        ]
        conflicts_lines = [
            f"### `{c.package}`\n"
            f"**Requested by**: {', '.join(f'`{k}` → `{v}`' for k, v in c.requested_by.items())}  \n"
            f"**Resolved to**: `{c.resolution or 'unresolvable'}`\n"
            for c in conflicts
        ]
        return REPORT_TEMPLATE.format(
            ecosystem=ecosystem,
            strategy=strategy,
            resolved_count=len(resolved),
            conflict_count=len(conflicts),
            cve_count=cve_count,
            license_count=len(license_issues),
            summary=conflict_explanation or "All dependencies resolved cleanly.",
            conflicts_section="\n".join(conflicts_lines) or "None.",
            security_section="\n".join(security_lines) or "No CVEs found.",
            lockfile=lockfile,
        )

    # ── Fallback (no LLM) ────────────────────────────────────────────────────

    def _fallback_explanation(self, conflicts: List[Conflict]) -> str:
        lines = [f"**{len(conflicts)} conflict(s) detected** (LLM offline — deterministic results only):\n"]
        for c in conflicts:
            requesters = ", ".join(
                f"`{k}` requires `{v}`" for k, v in c.requested_by.items()
            )
            lines.append(
                f"- **{c.package}**: {requesters} → "
                f"resolved to `{c.resolution or 'unresolvable'}`"
            )
        return "\n".join(lines)
