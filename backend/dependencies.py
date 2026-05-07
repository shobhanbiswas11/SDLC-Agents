"""
FastAPI dependency-injection helpers — exposes settings, the LLM service,
and any future shared resources.
"""
from __future__ import annotations

from fastapi import Depends

from core.config import Settings, get_settings
from core.services.llm_service import LLMService, get_llm_service


def settings_dep() -> Settings:
    return get_settings()


def llm_service_dep() -> LLMService:
    return get_llm_service()


__all__ = [
    "settings_dep",
    "llm_service_dep",
    "Settings",
    "LLMService",
    "Depends",
]
