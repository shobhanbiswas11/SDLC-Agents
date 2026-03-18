"""
Azure OpenAI client — authentication via Azure Entra ID (Service Principal).
"""

from __future__ import annotations

import logging

from azure.identity import ClientSecretCredential
from openai import AzureOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)

_client: AzureOpenAI | None = None


def get_azure_openai_client() -> AzureOpenAI | None:
    """
    Return a configured AzureOpenAI client authenticated via
    Azure Entra ID service-principal credentials.

    Returns None if Azure OpenAI is not configured.
    """
    global _client
    settings = get_settings()

    if not settings.has_azure_openai:
        logger.info("Azure OpenAI not configured — skipping AI features")
        return None

    if _client is not None:
        return _client

    credential = ClientSecretCredential(
        tenant_id=settings.azure_tenant_id,
        client_id=settings.azure_client_id,
        client_secret=settings.azure_client_secret,
    )

    token = credential.get_token("https://cognitiveservices.azure.com/.default")

    _client = AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_version=settings.azure_openai_api_version,
        api_key=token.token,
    )
    return _client
