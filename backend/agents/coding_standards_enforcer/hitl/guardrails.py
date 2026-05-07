"""
Lightweight input guardrails for the chat layer.

Goal: keep prompts on-topic (coding standards, fixes, style guides) and
reject obvious abuse before the LLM is invoked.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


# Hard cap on user message size — silently truncated above this.
MAX_USER_TEXT = 8_000

# Obvious "ignore previous instructions" jailbreak prompts.
_BLOCKLIST = [
    re.compile(r"ignore (all|previous) instructions", re.IGNORECASE),
    re.compile(r"system prompt", re.IGNORECASE),
    re.compile(r"developer mode", re.IGNORECASE),
]


@dataclass
class GuardrailResult:
    ok: bool
    text: str
    reason: str = ""


class GuardrailLayer:
    """Pre-flight check on user-supplied chat input."""

    def check_user_message(self, text: str) -> GuardrailResult:
        if not text or not text.strip():
            return GuardrailResult(ok=False, text="", reason="Empty message")

        clean = text.strip()
        if len(clean) > MAX_USER_TEXT:
            clean = clean[:MAX_USER_TEXT] + "\n\n... (truncated)"

        for pattern in _BLOCKLIST:
            if pattern.search(clean):
                return GuardrailResult(
                    ok=False,
                    text=clean,
                    reason=(
                        "I can only help with coding-standards questions and "
                        "fixes for the code you've shared in this session."
                    ),
                )

        return GuardrailResult(ok=True, text=clean)
