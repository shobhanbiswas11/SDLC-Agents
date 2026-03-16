# app/llm/llm_provider.py

import os
import time

from azure.identity import ClientSecretCredential
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

load_dotenv()

AZURE_OPENAI_ENDPOINT = "https://openaidev-westus.openai.azure.com/"
AZURE_OPENAI_API_VERSION = "2025-01-01-preview"
AZURE_OPENAI_CHATGPT_DEPLOYMENT = "gpt-4o"

# Cached instances to avoid re-creating credentials on every call
_cached_llm = None
_cached_token_expiry = 0


def get_llm():
    global _cached_llm, _cached_token_expiry

    # Reuse cached LLM if token hasn't expired (refresh 5 min before expiry)
    if _cached_llm and time.time() < _cached_token_expiry - 300:
        return _cached_llm

    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")

    if not all([tenant_id, client_id, client_secret]):
        raise ValueError("Azure credentials missing.")

    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )

    token = credential.get_token("https://cognitiveservices.azure.com/.default")

    _cached_llm = AzureChatOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version=AZURE_OPENAI_API_VERSION,
        deployment_name=AZURE_OPENAI_CHATGPT_DEPLOYMENT,
        azure_ad_token=token.token,
        temperature=0,
    )
    _cached_token_expiry = token.expires_on

    return _cached_llm
