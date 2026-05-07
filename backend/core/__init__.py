"""Core infrastructure — Coding Standards Enforcer."""
from .services.llm_service import get_llm_service, LLMService

__all__ = ["get_llm_service", "LLMService"]
