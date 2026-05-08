"""Core infrastructure — Dependency Resolver Agent."""
from .llm import get_llm_service, LLMService

__all__ = ["get_llm_service", "LLMService"]
