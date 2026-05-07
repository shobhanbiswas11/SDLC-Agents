"""
LLM service — singleton wrapper that returns a ready-to-use LangChain chat
model regardless of which provider backs it.
"""
from __future__ import annotations

import logging
from typing import Optional

from core.providers.azure_provider import AzureOpenAIProvider

logger = logging.getLogger(__name__)


class LLMService:
    """Lazy singleton-ish wrapper around an LLMProvider."""

    def __init__(self) -> None:
        self._provider = AzureOpenAIProvider()

    def available(self) -> bool:
        return self._provider.available()

    def reinitialise(self) -> None:
        """Force the underlying provider to rebuild its client on next call."""
        self._provider = AzureOpenAIProvider()

    def get_client(self):
        return self._provider.get_client()


_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


def get_llm():
    """Backward-compatible accessor — returns the underlying chat model."""
    return get_llm_service().get_client()
