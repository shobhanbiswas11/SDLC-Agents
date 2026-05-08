"""
LLM Configuration for Azure OpenAI
Handles authentication and model initialization
"""

import os
from typing import Optional
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class AzureOpenAIConfig:
    """Configuration for Azure OpenAI with LangChain"""

    def __init__(self):
        """Initialize config from environment variables"""
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
        self.deployment = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT", "gpt-4o")
        self.embedding_deployment = os.getenv(
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002"
        )

        # Azure AD credentials
        self.tenant_id = os.getenv("AZURE_TENANT_ID")
        self.client_id = os.getenv("AZURE_CLIENT_ID")
        self.client_secret = os.getenv("AZURE_CLIENT_SECRET")

        # API key (alternative auth method)
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")

        # Validate configuration
        self._validate()

    def _validate(self):
        """Validate that all required config is present"""
        if not self.endpoint:
            logger.warning("AZURE_OPENAI_ENDPOINT not set")

        if not self.api_key and not (self.client_id and self.client_secret):
            logger.warning("Neither API_KEY nor (CLIENT_ID + CLIENT_SECRET) configured")

        logger.info(f"Azure OpenAI Config: endpoint={self.endpoint}, deployment={self.deployment}")

    def is_configured(self) -> bool:
        """Check if LLM is properly configured"""
        return bool(
            self.endpoint
            and (self.api_key or (self.client_id and self.client_secret))
        )

    def get_llm_kwargs(self) -> dict:
        """Get kwargs for LangChain LLM initialization"""
        kwargs = {
            "deployment_name": self.deployment,
            "temperature": 0.3,  # Lower temp for more deterministic responses
            "max_tokens": 2000,
        }

        if self.api_key:
            kwargs["api_key"] = self.api_key
        else:
            # Use Azure AD authentication
            kwargs["azure_ad_token_provider"] = self._get_token_provider()

        return kwargs

    def _get_token_provider(self):
        """Get token provider for Azure AD"""
        try:
            from azure.identity import ClientSecretCredential

            credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret,
            )

            def token_provider():
                token = credential.get_token("https://cognitiveservices.azure.com/.default")
                return token.token

            return token_provider
        except ImportError:
            logger.error("azure-identity package not installed")
            return None


# Global config instance
_config: Optional[AzureOpenAIConfig] = None


def get_llm_config() -> AzureOpenAIConfig:
    """Get or create global LLM config"""
    global _config
    if _config is None:
        _config = AzureOpenAIConfig()
    return _config
