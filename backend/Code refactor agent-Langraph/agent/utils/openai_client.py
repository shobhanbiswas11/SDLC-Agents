"""
agent/utils/openai_client.py — Cached Azure OpenAI async client factory.

The client is refreshed every 30 minutes to handle token expiry when using
ClientSecretCredential (Azure AD service-principal auth).
"""

from __future__ import annotations

import os
import time

from core.logging import get_logger

logger = get_logger(__name__)

_cached_client = None
_cached_client_time = 0.0
_CLIENT_TTL = 1800  # 30 minutes


def get_openai_client():
    """Return a cached AsyncAzureOpenAI client, refreshing every 30 minutes."""
    global _cached_client, _cached_client_time

    if _cached_client and (time.time() - _cached_client_time) < _CLIENT_TTL:
        return _cached_client

    from openai import AsyncAzureOpenAI
    from azure.identity import ClientSecretCredential

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
    tenant_id = os.getenv("AZURE_TENANT_ID", "")
    client_id = os.getenv("AZURE_CLIENT_ID", "")
    client_secret = os.getenv("AZURE_CLIENT_SECRET", "")

    if tenant_id and client_id and client_secret:
        logger.debug("Building Azure OpenAI client via ClientSecretCredential")
        cred = ClientSecretCredential(tenant_id, client_id, client_secret)
        token = cred.get_token("https://cognitiveservices.azure.com/.default")
        client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_version=api_version,
            api_key=token.token,
        )
    else:
        logger.debug("Building Azure OpenAI client via API key")
        client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_version=api_version,
            api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
        )

    _cached_client = client
    _cached_client_time = time.time()
    return client
