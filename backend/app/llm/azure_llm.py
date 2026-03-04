import os
from azure.identity import ClientSecretCredential
from langchain_openai import AzureChatOpenAI
from .base import BaseLLM


class AzureLLM(BaseLLM):

    def __init__(self):
        self.tenant_id = os.getenv("AZURE_TENANT_ID")
        self.client_id = os.getenv("AZURE_CLIENT_ID")
        self.client_secret = os.getenv("AZURE_CLIENT_SECRET")
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        self.deployment = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT")

        credential = ClientSecretCredential(
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            client_secret=self.client_secret
        )

        token = credential.get_token("https://cognitiveservices.azure.com/.default")

        # LangChain-compatible llm (used by the agent)
        self.llm = AzureChatOpenAI(
            azure_endpoint=self.endpoint,
            api_version=self.api_version,
            azure_deployment=self.deployment,
            azure_ad_token=token.token,
            temperature=0
        )

    def generate(self, prompt: str) -> str:
        response = self.llm.invoke(prompt)
        return response.content
