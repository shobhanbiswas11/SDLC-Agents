"""
Application configuration — loaded from environment variables via pydantic-settings.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global settings, populated from env vars / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── General ───────────────────────────────────────────────
    app_name: str = "Dependency Resolver Agent"
    debug: bool = False
    clone_dir: str = "/tmp/dependency-resolver-repos"

    # ── Azure OpenAI ──────────────────────────────────────────
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-12-01-preview"
    azure_openai_chatgpt_deployment: str = ""
    azure_openai_embedding_deployment: str = ""

    # ── Cache ─────────────────────────────────────────────────
    cache_dir: str = "/tmp/dependency-resolver-cache"
    cache_ttl: int = 3600  # seconds

    @property
    def clone_path(self) -> Path:
        return Path(self.clone_dir)

    @property
    def has_azure_openai(self) -> bool:
        return bool(self.azure_openai_endpoint and self.azure_openai_chatgpt_deployment)


@lru_cache
def get_settings() -> Settings:
    return Settings()
