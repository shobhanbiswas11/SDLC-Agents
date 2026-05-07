"""
Provider protocol — common surface every cloud-LLM adapter must satisfy.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Minimal contract for a chat-LLM provider."""

    def get_client(self) -> object:
        """Return a LangChain chat model instance ready to invoke."""
        ...

    def available(self) -> bool:
        """True when credentials and endpoint are valid."""
        ...
