"""
LangChain LLM wrapper for Azure OpenAI — used by the AI reasoning modules.
"""

from __future__ import annotations

import logging

from azure.identity import ClientSecretCredential
from langchain_openai import AzureChatOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)

_llm: AzureChatOpenAI | None = None


def get_langchain_llm() -> AzureChatOpenAI | None:
    """
    Return a LangChain AzureChatOpenAI instance authenticated via Azure Entra ID.

    Returns None when Azure OpenAI is not configured.
    """
    global _llm
    settings = get_settings()

    if not settings.has_azure_openai:
        logger.info("Azure OpenAI not configured — AI features disabled")
        return None

    if _llm is not None:
        return _llm

    credential = ClientSecretCredential(
        tenant_id=settings.azure_tenant_id,
        client_id=settings.azure_client_id,
        client_secret=settings.azure_client_secret,
    )

    token = credential.get_token("https://cognitiveservices.azure.com/.default")

    _llm = AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_version=settings.azure_openai_api_version,
        azure_deployment=settings.azure_openai_chatgpt_deployment,
        api_key=token.token,
        temperature=0.3,
    )
    return _llm
