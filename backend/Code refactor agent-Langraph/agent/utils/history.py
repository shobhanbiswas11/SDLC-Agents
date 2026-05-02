"""
agent/utils/history.py — Conversation history management helpers.

Provides token counting and history trimming so the LLM never receives
a context window that exceeds the model's limit.
"""

from __future__ import annotations

from core.logging import get_logger

logger = get_logger(__name__)

_MAX_TOKENS = 120_000


def get_token_count(messages: list[dict], model: str = "gpt-4o") -> int:
    """
    Return an approximate token count for a list of OpenAI-format messages.

    Uses tiktoken when available; falls back to a character-based estimate
    (÷4) when the library is not installed.
    """
    try:
        import tiktoken

        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")

        num_tokens = 0
        for message in messages:
            num_tokens += 3  # per-message overhead
            for value in message.values():
                if value:
                    num_tokens += len(encoding.encode(str(value)))
        num_tokens += 3  # reply priming
        return num_tokens

    except ImportError:
        total_chars = sum(len(str(v)) for m in messages for v in m.values() if v)
        return total_chars // 4


def trim_history(messages: list[dict], max_tokens: int = _MAX_TOKENS) -> list[dict]:
    """
    Keep the system message plus as many recent messages as fit within *max_tokens*.

    Oldest messages are dropped first. Two invariants are maintained:
    - A ``tool`` result message is never left without the preceding ``assistant``
      message that requested it.
    - Orphaned leading ``tool`` messages (whose ``assistant`` call was already
      dropped) are also removed.

    Args:
        messages:   Full conversation history in OpenAI message format.
        max_tokens: Hard upper bound on total tokens.

    Returns:
        Trimmed list, always beginning with the system message (if present).
    """
    system_msgs = [m for m in messages if m.get("role") == "system"]
    non_system = [m for m in messages if m.get("role") != "system"]

    while len(non_system) > 1:
        if get_token_count(system_msgs + non_system) <= max_tokens:
            break

        removed = non_system.pop(0)

        # Guard: never orphan tool results that belong to the removed call
        if removed.get("role") == "assistant" and removed.get("tool_calls"):
            while non_system and non_system[0].get("role") == "tool":
                non_system.pop(0)

        # Guard: drop any orphaned leading tool messages
        while non_system and non_system[0].get("role") == "tool":
            non_system.pop(0)

    trimmed = system_msgs + non_system
    if len(trimmed) < len(messages):
        logger.debug("History trimmed from %d → %d messages", len(messages), len(trimmed))
    return trimmed
