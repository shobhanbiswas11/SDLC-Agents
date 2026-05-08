"""LLM integration — Azure AD authenticated AzureChatOpenAI."""
from .service import get_llm_service, LLMService

__all__ = ["get_llm_service", "LLMService"]
