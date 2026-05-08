"""
LLM streaming helper — bridges async generator → WebSocket frames.
"""
from __future__ import annotations
import logging
from typing import AsyncIterator, Callable, Awaitable

logger = logging.getLogger(__name__)


async def stream_to_ws(
    token_gen: AsyncIterator[str],
    emit: Callable[[str, bool], Awaitable[None]],
) -> str:
    """
    Consume token_gen, calling emit(token, done) for each token.
    Returns the full concatenated text.
    """
    full_text = []
    try:
        async for token in token_gen:
            full_text.append(token)
            await emit(token, False)
        await emit("", True)
    except Exception as exc:
        logger.error(f"stream_to_ws error: {exc}")
        await emit("", True)
    return "".join(full_text)
