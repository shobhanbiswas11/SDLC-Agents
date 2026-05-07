"""
Application settings — sourced from environment variables / .env.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from pydantic import BaseModel


class Settings(BaseModel):
    """Strongly-typed application settings."""

    # ── Azure OpenAI ─────────────────────────────────────────
    azure_openai_endpoint: str = "https://openaidev-westus.openai.azure.com/"
    azure_openai_api_version: str = "2025-01-01-preview"
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_api_key: Optional[str] = None

    # ── Azure AD (service-principal) ────────────────────────
    azure_tenant_id: Optional[str] = None
    azure_client_id: Optional[str] = None
    azure_client_secret: Optional[str] = None

    # ── Server ───────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000

    # ── Scan / repo limits ───────────────────────────────────
    max_file_size_for_editor: int = 100_000   # bytes
    max_file_size_for_llm: int = 15_000       # bytes
    scan_max_workers: int = 8


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton accessor that reads from os.environ at import time."""
    return Settings(
        azure_openai_endpoint=os.getenv(
            "AZURE_OPENAI_ENDPOINT",
            "https://openaidev-westus.openai.azure.com/",
        ),
        azure_openai_api_version=os.getenv(
            "AZURE_OPENAI_API_VERSION", "2025-01-01-preview"
        ),
        azure_openai_deployment=os.getenv(
            "AZURE_OPENAI_CHATGPT_DEPLOYMENT", "gpt-4o"
        ),
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_tenant_id=os.getenv("AZURE_TENANT_ID"),
        azure_client_id=os.getenv("AZURE_CLIENT_ID"),
        azure_client_secret=os.getenv("AZURE_CLIENT_SECRET"),
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
    )
