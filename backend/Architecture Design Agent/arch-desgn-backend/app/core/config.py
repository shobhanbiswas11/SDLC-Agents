"""
Application configuration — loaded from environment variables / .env file.

Switch LLM providers by setting LLM_PROVIDER in your .env:
    LLM_PROVIDER=gemini      (default)
    LLM_PROVIDER=azure
    LLM_PROVIDER=openai
"""

from __future__ import annotations

from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseModel):
    # ─── LLM Provider Switch ───
    # Supported values: "gemini", "azure", "openai"
    llm_provider: str = os.getenv("LLM_PROVIDER", "gemini").lower().strip()

    # ─── Common ───
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))

    # ─── Google Gemini ───
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # ─── Azure OpenAI (Entra ID / AAD Auth) ───
    azure_tenant_id: str = os.getenv("AZURE_TENANT_ID", "")
    azure_client_id: str = os.getenv("AZURE_CLIENT_ID", "")
    azure_client_secret: str = os.getenv("AZURE_CLIENT_SECRET", "")
    azure_openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_openai_api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01")
    azure_openai_chatgpt_deployment: str = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT", "")
    azure_openai_embedding_deployment: str = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "")
    azure_openai_token_scope: str = os.getenv("AZURE_OPENAI_TOKEN_SCOPE", "https://cognitiveservices.azure.com/.default")

    # ─── OpenAI (direct) ───
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


settings = Settings()