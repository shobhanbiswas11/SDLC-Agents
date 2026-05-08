"""
LLM Service — AzureChatOpenAI via Azure AD ClientSecretCredential.
No API key required: authenticates with AZURE_TENANT_ID / CLIENT_ID / CLIENT_SECRET.
"""
from __future__ import annotations
import logging
import os
from typing import Optional, List, Dict, AsyncIterator

# Load .env FIRST — must happen before any os.getenv() call.
# dotenv is a no-op when variables are already in the environment.
try:
    from dotenv import load_dotenv
    # Walk up until we find a .env file (handles running from backend/ or project root)
    import pathlib
    _here = pathlib.Path(__file__).resolve()
    for _parent in [_here.parents[3], _here.parents[2], _here.parents[1], _here.parent]:
        _env = _parent / ".env"
        if _env.exists():
            load_dotenv(_env, override=False)
            break
except ImportError:
    pass  # python-dotenv not installed — rely on shell environment

logger = logging.getLogger(__name__)


def _build_llm():
    """
    Build AzureChatOpenAI using Azure AD ClientSecretCredential.
    Returns None gracefully if credentials are missing.
    """
    endpoint      = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip().rstrip("/")
    api_version   = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview").strip()
    deployment    = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT", "gpt-4o").strip()
    tenant_id     = os.getenv("AZURE_TENANT_ID", "").strip()
    client_id     = os.getenv("AZURE_CLIENT_ID", "").strip()
    client_secret = os.getenv("AZURE_CLIENT_SECRET", "").strip()

    missing = [k for k, v in {
        "AZURE_OPENAI_ENDPOINT": endpoint,
        "AZURE_TENANT_ID":       tenant_id,
        "AZURE_CLIENT_ID":       client_id,
        "AZURE_CLIENT_SECRET":   client_secret,
    }.items() if not v]

    if missing:
        logger.info(
            "LLM: Azure AD credentials not set (%s) — "
            "running without LLM explanations. "
            "Set these in backend/.env to enable gpt-4o.",
            ", ".join(missing),
        )
        return None

    try:
        from azure.identity import ClientSecretCredential
        from langchain_openai import AzureChatOpenAI

        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )

        def token_provider() -> str:
            return credential.get_token(
                "https://cognitiveservices.azure.com/.default"
            ).token

        llm = AzureChatOpenAI(
            azure_endpoint=endpoint,
            api_version=api_version,
            azure_deployment=deployment,
            azure_ad_token_provider=token_provider,
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.2")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1500")),
            streaming=True,
        )
        logger.info(
            "LLM: AzureChatOpenAI ready (endpoint=%s, deployment=%s)",
            endpoint, deployment,
        )
        return llm

    except ImportError as exc:
        logger.warning(
            "LLM: missing package — %s. "
            "Run: pip install langchain-openai azure-identity --break-system-packages", exc
        )
        return None
    except Exception as exc:
        logger.warning("LLM: initialisation failed — %s", exc)
        return None


class LLMService:
    def __init__(self):
        self.llm = _build_llm()

    def available(self) -> bool:
        return self.llm is not None

    def reinitialise(self) -> bool:
        """Re-attempt LLM init (call from startup hook after .env is confirmed loaded)."""
        if self.llm is None:
            self.llm = _build_llm()
        return self.available()

    async def astream(self, prompt: str) -> AsyncIterator[str]:
        if not self.llm:
            yield "(LLM not configured — explanation unavailable)"
            return
        try:
            async for chunk in self.llm.astream(prompt):
                yield chunk.content
        except Exception as exc:
            logger.error("astream error: %s", exc)
            yield f"(LLM error: {exc})"

    async def astream_messages(self, messages: List[Dict]) -> AsyncIterator[str]:
        if not self.llm:
            yield "(LLM not configured)"
            return
        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

        lc_messages = []
        for m in messages:
            role, content = m.get("role", "user"), m.get("content", "")
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))

        try:
            async for chunk in self.llm.astream(lc_messages):
                yield chunk.content
        except Exception as exc:
            logger.error("astream_messages error: %s", exc)
            yield f"(LLM error: {exc})"


# ── Module-level singleton ────────────────────────────────────────────────────

_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    global _service
    if _service is None:
        _service = LLMService()
    return _service
