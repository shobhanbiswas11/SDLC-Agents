import os
from dotenv import load_dotenv
from azure.identity import ClientSecretCredential, get_bearer_token_provider
from openai import AzureOpenAI

load_dotenv()

def get_client():
    credential = ClientSecretCredential(
        tenant_id=os.getenv("AZURE_TENANT_ID"),
        client_id=os.getenv("AZURE_CLIENT_ID"),
        client_secret=os.getenv("AZURE_CLIENT_SECRET"),
    )

    token_provider = get_bearer_token_provider(
        credential,
        "https://cognitiveservices.azure.com/.default"
    )

    client = AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_ad_token_provider=token_provider,
    )

    return client

def test_embedding():
    print("in")
    deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002") # fallback to prevent value error if missing from env

    print("Using deployment:", deployment)

    client = get_client()

    texts = [
        "User login failed",
        "Authentication error occurred",
        "Payment successful"
    ]

    try:
        response = client.embeddings.create(
            model=deployment,
            input=texts
        )

        embeddings = [item.embedding for item in response.data]
        print("\n✅ Embedding successful!\n")

    except Exception as e:
        print("\n❌ Embedding failed:")
        print(type(e)._name_, "-", e)

if __name__ == "_main_":
    test_embedding()