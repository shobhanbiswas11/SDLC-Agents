"""Custom exception types used across services and agents."""
from __future__ import annotations


class AgentError(Exception):
    """Base class for all agent-level failures."""


class LLMUnavailableError(AgentError):
    """Raised when no LLM provider can serve the request."""


class UnsupportedLanguageError(AgentError):
    """Raised when a code analysis is requested for a language we don't handle."""


class RepositoryError(AgentError):
    """Raised when cloning, listing, or reading a repo fails."""
