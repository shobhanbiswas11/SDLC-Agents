"""
tools/interaction_tools.py — Human-in-the-loop tool handlers.

Handlers:
  handle_ask_user — signals the workflow to pause and ask the human a question.
                    The actual interrupt() is issued in tool_node.py; this
                    handler is a lightweight stub retained for symmetry so the
                    TOOL_HANDLERS dispatch table always has a callable.
"""

from __future__ import annotations

from core.logging import get_logger

logger = get_logger(__name__)


async def handle_ask_user(question: str, **_) -> dict:
    """
    Stub handler for the ask_user tool.

    The real pause-and-resume logic is handled by ``tool_node.py`` which calls
    ``langgraph.types.interrupt(question)`` directly. This stub exists so the
    dispatch table is complete and unit-testable without a running LangGraph.
    """
    logger.info("ask_user: '%s'", question[:80])
    return {"status": "ask_user", "question": question}
