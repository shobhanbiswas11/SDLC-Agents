"""
LLM Abstraction Layer


Provides a unified `get_llm()` factory that returns a LangChain chat model
based on the configured provider.

Supported providers (set via LLM_PROVIDER env var):
     "gemini"  → Google Gemini (default)
     "azure"   → Azure OpenAI Service
     "openai"  → OpenAI (direct API)

All agents call `get_llm()` without knowing which provider is behind it.
The returned object is always a LangChain BaseChatModel that supports
`.invoke()`, `.with_structured_output()`, etc.

Usage:
    from app.agents._llm import get_llm

    llm = get_llm(temperature=0.2)
    llm_with_schema = llm.with_structured_output(MyPydanticModel)
    result = llm_with_schema.invoke(messages)
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

from langchain_core.language_models import BaseChatModel

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_llm(temperature: Optional[float] = None) -> BaseChatModel:
    """Return a LangChain chat model for the configured provider.

    Args:
        temperature: Override the default temperature for this call.
                     If None, uses the global LLM_TEMPERATURE setting.

    Returns:
        A LangChain BaseChatModel instance (Gemini, AzureChatOpenAI, or ChatOpenAI).

    Raises:
        ValueError: If the provider is not recognized or required env vars are missing.
    """
    temp = settings.temperature if temperature is None else temperature
    provider = settings.llm_provider

    if provider == "gemini":
        return _build_gemini(temp)
    elif provider == "azure":
        return _build_azure(temp)
    elif provider == "openai":
        return _build_openai(temp)
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: '{provider}'. "
            f"Supported values: 'gemini', 'azure', 'openai'"
        )


# ─── Provider Builders ───

def _build_gemini(temperature: float) -> BaseChatModel:
    """Build a Google Gemini chat model via langchain-google-genai."""
    if not settings.google_api_key:
        raise ValueError(
            "GOOGLE_API_KEY is not set. "
            "Set it in your .env file to use the Gemini provider."
        )

    from langchain_google_genai import ChatGoogleGenerativeAI

    logger.info("Using LLM provider: Gemini (%s)", settings.gemini_model)
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=temperature,
    )


def _build_azure(temperature: float) -> BaseChatModel:
    """Build an Azure OpenAI chat model via langchain-openai with Entra ID (AAD) auth."""
    missing = []
    if not settings.azure_tenant_id:
        missing.append("AZURE_TENANT_ID")
    if not settings.azure_client_id:
        missing.append("AZURE_CLIENT_ID")
    if not settings.azure_client_secret:
        missing.append("AZURE_CLIENT_SECRET")
    if not settings.azure_openai_endpoint:
        missing.append("AZURE_OPENAI_ENDPOINT")
    if not settings.azure_openai_chatgpt_deployment:
        missing.append("AZURE_OPENAI_CHATGPT_DEPLOYMENT")
    if missing:
        raise ValueError(
            f"Missing Azure config: {', '.join(missing)}. "
            f"Set them in your .env file to use the Azure provider."
        )

    from azure.identity import ClientSecretCredential
    from langchain_openai import AzureChatOpenAI

    # Subclass that defaults to function_calling for with_structured_output().
    # Azure's default json_schema mode requires additionalProperties:false on
    # all objects, which is incompatible with Dict[str, Any] fields.
    class _AzureChatOpenAICompat(AzureChatOpenAI):
        def with_structured_output(self, schema, **kwargs):
            kwargs.setdefault("method", "function_calling")
            return super().with_structured_output(schema, **kwargs)

    # Obtain AAD token via Client Secret Credential
    credential = ClientSecretCredential(
        tenant_id=settings.azure_tenant_id,
        client_id=settings.azure_client_id,
        client_secret=settings.azure_client_secret,
    )
    token = credential.get_token(settings.azure_openai_token_scope)

    logger.info(
        "Using LLM provider: Azure OpenAI (%s @ %s) with Entra ID auth",
        settings.azure_openai_chatgpt_deployment,
        settings.azure_openai_endpoint,
    )
    return _AzureChatOpenAICompat(
        azure_deployment=settings.azure_openai_chatgpt_deployment,
        azure_endpoint=settings.azure_openai_endpoint,
        azure_ad_token=token.token,
        api_version=settings.azure_openai_api_version,
        temperature=temperature,
    )


def _build_openai(temperature: float) -> BaseChatModel:
    """Build a direct OpenAI chat model via langchain-openai."""
    if not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY is not set. "
            "Set it in your .env file to use the OpenAI provider."
        )

    from langchain_openai import ChatOpenAI

    logger.info("Using LLM provider: OpenAI (%s)", settings.openai_model)
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=temperature,
    )


@lru_cache(maxsize=1)
def get_provider_info() -> dict:
    """Return info about the active provider (for health check / debugging)."""
    provider = settings.llm_provider
    info = {"provider": provider}

    if provider == "gemini":
        info["model"] = settings.gemini_model
        info["configured"] = bool(settings.google_api_key)
    elif provider == "azure":
        info["model"] = settings.azure_openai_chatgpt_deployment
        info["endpoint"] = settings.azure_openai_endpoint
        info["api_version"] = settings.azure_openai_api_version
        info["auth"] = "entra_id"
        info["configured"] = all([
            settings.azure_tenant_id,
            settings.azure_client_id,
            settings.azure_client_secret,
            settings.azure_openai_endpoint,
            settings.azure_openai_chatgpt_deployment,
        ])
    elif provider == "openai":
        info["model"] = settings.openai_model
        info["configured"] = bool(settings.openai_api_key)
    else:
        info["configured"] = False
        info["error"] = f"Unknown provider: {provider}"

    return info