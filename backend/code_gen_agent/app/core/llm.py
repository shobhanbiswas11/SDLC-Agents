import os
from dotenv import load_dotenv

from langchain_openai import AzureChatOpenAI, ChatOpenAI
from azure.identity import ClientSecretCredential, get_bearer_token_provider

load_dotenv()


def get_llm():
    provider = os.getenv("LLM_PROVIDER", "azure")

    if provider == "azure":
        # Azure AD service principal authentication
        credential = ClientSecretCredential(
            tenant_id=os.getenv("AZURE_TENANT_ID"),
            client_id=os.getenv("AZURE_CLIENT_ID"),
            client_secret=os.getenv("AZURE_CLIENT_SECRET"),
        )
        token_provider = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )

        return AzureChatOpenAI(
            azure_deployment=os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
            azure_ad_token_provider=token_provider,
            temperature=0,
        )

    elif provider == "groq":
        return ChatOpenAI(
            model="llama-3.1-8b-instant",
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0,
        )

    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")