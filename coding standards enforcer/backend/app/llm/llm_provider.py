import os
from dotenv import load_dotenv
from azure.identity import ClientSecretCredential
from langchain_openai import AzureChatOpenAI

load_dotenv()

AZURE_OPENAI_ENDPOINT = "https://openaidev-westus.openai.azure.com/"
AZURE_OPENAI_API_VERSION = "2025-01-01-preview"
AZURE_OPENAI_CHATGPT_DEPLOYMENT = "gpt-4o"


def get_llm():
    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")

    if not all([tenant_id, client_id, client_secret]):
        raise ValueError(
            f"Azure credentials missing: "
            f"TENANT={tenant_id}, CLIENT={client_id}, SECRET={'SET' if client_secret else None}"
        )

    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret
    )

    token = credential.get_token(
        "https://cognitiveservices.azure.com/.default"
    )

    return AzureChatOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version=AZURE_OPENAI_API_VERSION,
        deployment_name=AZURE_OPENAI_CHATGPT_DEPLOYMENT,
        azure_ad_token=token.token,
        temperature=0
    )