"""
Azure OpenAI provider — authenticates with Azure AD ClientSecretCredential
and exposes a cached AzureChatOpenAI instance.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from azure.identity import ClientSecretCredential
from langchain_openai import AzureChatOpenAI

from core.config import get_settings

logger = logging.getLogger(__name__)


class AzureOpenAIProvider:
    """Caches an AzureChatOpenAI client and refreshes its AAD token."""

    def __init__(self) -> None:
        self._client: Optional[AzureChatOpenAI] = None
        self._token_expiry: float = 0.0

    def available(self) -> bool:
        s = get_settings()
        if s.azure_openai_api_key:
            return bool(s.azure_openai_endpoint)
        return all(
            [
                s.azure_tenant_id,
                s.azure_client_id,
                s.azure_client_secret,
                s.azure_openai_endpoint,
            ]
        )

    def get_client(self) -> AzureChatOpenAI:
        # Reuse cached client if AAD token still valid (refresh 5 min before expiry).
        if self._client and time.time() < self._token_expiry - 300:
            return self._client

        s = get_settings()

        if s.azure_openai_api_key:
            # API-key auth path (alternative to AAD).
            self._client = AzureChatOpenAI(
                azure_endpoint=s.azure_openai_endpoint,
                api_version=s.azure_openai_api_version,
                deployment_name=s.azure_openai_deployment,
                api_key=s.azure_openai_api_key,
                temperature=0,
            )
            # Treat API-key clients as long-lived.
            self._token_expiry = time.time() + 60 * 60 * 24
            return self._client

        if not all(
            [s.azure_tenant_id, s.azure_client_id, s.azure_client_secret]
        ):
            raise ValueError(
                "Azure credentials missing — set AZURE_TENANT_ID, "
                "AZURE_CLIENT_ID, AZURE_CLIENT_SECRET (or AZURE_OPENAI_API_KEY)."
            )

        credential = ClientSecretCredential(
            tenant_id=s.azure_tenant_id,
            client_id=s.azure_client_id,
            client_secret=s.azure_client_secret,
        )

        token = credential.get_token("https://cognitiveservices.azure.com/.default")

        self._client = AzureChatOpenAI(
            azure_endpoint=s.azure_openai_endpoint,
            api_version=s.azure_openai_api_version,
            deployment_name=s.azure_openai_deployment,
            azure_ad_token=token.token,
            temperature=0,
        )
        self._token_expiry = float(token.expires_on)
        logger.info(
            "AzureOpenAIProvider authenticated (token expires at %s)",
            self._token_expiry,
        )
        return self._client
