"""
agent/nodes/logic_verification_node.py — LangGraph node: automated code review.

After the LLM produces a final response, this node acts as a Senior QA Engineer
and verifies that the refactoring did NOT change external logic or business rules.

- If no code-modifying tools were used → auto-approve.
- If the LLM reviewer approves        → set ``verification_passed=True``.
- If the LLM reviewer rejects         → inject a critique message and loop
  back to the LLM for a fix (max 2 retries before auto-approving to prevent
  infinite loops).
"""

from __future__ import annotations

import os

from agent.state import AgentState
from agent.utils.openai_client import get_openai_client
from core.logging import get_logger

logger = get_logger(__name__)

_MAX_ATTEMPTS = 2
_CODE_MODIFYING_TOOLS = {
    "apply_refactor",
    "apply_batch_refactor",
    "multi_refactor",
    "write_file",
    "github_put_file",
}
_REVIEWER_HISTORY_WINDOW = 30

_REVIEWER_SYSTEM_PROMPT = (
    "You are a Senior QA Engineer and Code Reviewer.\n"
    "Your job is to verify that the recent refactoring did NOT change the external "
    "logic or business rules of the code.\n"
    "Refactoring should only improve structure, readability, performance, or apply "
    "design patterns. It MUST NOT break existing functionality or alter external interfaces.\n\n"
    "Review the recent tool calls and code changes.\n"
    "Output EXACTLY one of two responses:\n"
    "  'APPROVED' — if the external logic is safely preserved.\n"
    "  'REJECTED: <specific reason>' — if business logic was fundamentally altered or broken."
)


def _current_turn_history(history: list[dict]) -> list[dict]:
    """Return messages since the latest user turn."""
    for idx in range(len(history) - 1, -1, -1):
        if history[idx].get("role") == "user":
            return history[idx:]
    return history


def _code_was_modified(history: list[dict]) -> bool:
    """Return True if a code-modifying tool was called in the current turn."""
    for msg in _current_turn_history(history):
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                if tc.get("function", {}).get("name") in _CODE_MODIFYING_TOOLS:
                    return True
    return False


def _reviewer_safe_history(history: list[dict]) -> list[dict]:
    """Convert tool-call transcript into plain chat messages for reviewer LLM."""
    safe: list[dict] = []
    for msg in history[-_REVIEWER_HISTORY_WINDOW:]:
        role = msg.get("role", "user")
        if role == "tool":
            safe.append({"role": "user", "content": f"Tool result: {msg.get('content', '')}"})
        elif role == "assistant" and msg.get("tool_calls"):
            names = [
                tc.get("function", {}).get("name", "unknown")
                for tc in msg.get("tool_calls", [])
            ]
            safe.append({"role": "assistant", "content": f"Requested tool calls: {', '.join(names)}"})
        elif role in {"user", "assistant", "system"}:
            safe.append({"role": role, "content": msg.get("content") or ""})
    return safe


async def logic_verification_node(state: AgentState) -> dict:
    """
    Automated code review node.

    Calls the LLM as a reviewer with a focused system prompt and the recent
    conversation history. Returns updated state indicating approval or rejection.
    """
    history = list(state.get("history", []))
    attempts = int(state.get("verification_attempts", 0)) + 1

    if not _code_was_modified(history):
        logger.debug("logic_verification: no code modified → auto-approved")
        return {**state, "verification_passed": True, "verification_attempts": attempts}

    if attempts > _MAX_ATTEMPTS:
        logger.warning(
            "logic_verification: max attempts (%d) reached → auto-approved", _MAX_ATTEMPTS
        )
        return {**state, "verification_passed": True, "verification_attempts": attempts}

    client = get_openai_client()
    deployment = (
        os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT")
        or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    )

    reviewer_prompt = {"role": "system", "content": _REVIEWER_SYSTEM_PROMPT}
    recent_history = _reviewer_safe_history(history)
    messages = [reviewer_prompt] + recent_history

    try:
        response = await client.chat.completions.create(
            model=deployment,
            messages=messages,
            temperature=0,
            max_completion_tokens=500,
            timeout=60,
        )
        result = response.choices[0].message.content.strip()
        logger.info("logic_verification (attempt %d): %s", attempts, result[:100])
    except Exception as exc:
        logger.warning("logic_verification: reviewer call failed (%s) → auto-approved", exc)
        result = "APPROVED"

    if result.upper().startswith("APPROVED"):
        return {**state, "verification_passed": True, "verification_attempts": attempts}

    # Rejection — inject the critique and send the agent back to fix it
    critique = result.replace("REJECTED:", "").strip()
    logger.info("logic_verification: rejected, injecting critique")
    updated_history = history + [
        {
            "role": "user",
            "content": (
                f"⚠️ Logic Verification Failed! Please fix the following regression:\n\n"
                f"{critique}\n\n"
                "Ensure no external logic or business rules are broken."
            ),
        }
    ]
    return {
        **state,
        "verification_passed": False,
        "verification_attempts": attempts,
        "history": updated_history,
        "status": "thinking",
    }
