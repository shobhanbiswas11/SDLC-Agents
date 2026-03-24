import os
import numpy as np
from collections import defaultdict
from sklearn.cluster import DBSCAN

from dotenv import load_dotenv
from azure.identity import ClientSecretCredential, get_bearer_token_provider
from openai import AzureOpenAI

load_dotenv()


def get_azure_client():
    # credential = ClientSecretCredential(
    #     tenant_id=os.getenv("AZURE_TENANT_ID"),
    #     client_id=os.getenv("AZURE_CLIENT_ID"),
    #     client_secret=os.getenv("AZURE_CLIENT_SECRET"),
    # )

    # token_provider = get_bearer_token_provider(
    #     credential,
    #     "https://cognitiveservices.azure.com/.default"
    # )

    # client = AzureOpenAI(
    #     azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    #     api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    #     azure_ad_token_provider=token_provider,
    # )

    # return client


    try:
        credential = ClientSecretCredential(
            tenant_id=os.getenv("AZURE_TENANT_ID"),
            client_id=os.getenv("AZURE_CLIENT_ID"),
            client_secret=os.getenv("AZURE_CLIENT_SECRET"),
        )
        token = credential.get_token("https://cognitiveservices.azure.com/.default")
        return AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_ad_token=token.token,
        )
    except Exception as e:
        raise ValueError(
            "Failed to initialize Azure OpenAI with Microsoft Entra credentials. "
            "Verify AZURE_CLIENT_ID is the Application (client) ID of an Entra App Registration, "
            "or set AZURE_OPENAI_API_KEY to use key-based auth. "
            f"Original error: {e}"
        )


# def get_azure_client() -> AzureOpenAI:
# if AZURE_OPENAI_API_KEY.strip():
#     return AzureOpenAI(
#         azure_endpoint=AZURE_OPENAI_ENDPOINT,
#         api_version=AZURE_OPENAI_API_VERSION,
#         api_key=AZURE_OPENAI_API_KEY.strip(),
#     )

# if not (AZURE_TENANT_ID.strip() and AZURE_CLIENT_ID.strip() and AZURE_CLIENT_SECRET.strip()):
#     raise ValueError(
#         "Azure auth is not configured. Set AZURE_OPENAI_API_KEY or set all of "
#         "AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET."
#     )

# try:
#     credential = ClientSecretCredential(
#         tenant_id=AZURE_TENANT_ID.strip(),
#         client_id=AZURE_CLIENT_ID.strip(),
#         client_secret=AZURE_CLIENT_SECRET.strip(),
#     )
#     token = credential.get_token("https://cognitiveservices.azure.com/.default")
#     return AzureOpenAI(
#         azure_endpoint=AZURE_OPENAI_ENDPOINT,
#         api_version=AZURE_OPENAI_API_VERSION,
#         azure_ad_token=token.token,
#     )
# except Exception as e:
#     raise ValueError(
#         "Failed to initialize Azure OpenAI with Microsoft Entra credentials. "
#         "Verify AZURE_CLIENT_ID is the Application (client) ID of an Entra App Registration, "
#         "or set AZURE_OPENAI_API_KEY to use key-based auth. "
#         f"Original error: {e}"
#     )



EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")

# client = get_azure_client()

def get_embeddings(texts, batch_size=50, threshold=100):
    client = get_azure_client()

    # SMALL → single call
    if len(texts) <= threshold:
        try:
            response = client.embeddings.create(
                model=EMBEDDING_DEPLOYMENT,
                input=texts
            )
            return [item.embedding for item in response.data]

        except Exception as e:
            print(f"Embedding failed: {e}")
            return [[0.0] * 1536 for _ in texts]

    # LARGE → batching
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]

        try:
            response = client.embeddings.create(
                model=EMBEDDING_DEPLOYMENT,
                input=batch
            )

            print("exit")

            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

        except Exception as e:
            print(f"Batch failed: {e}")
            all_embeddings.extend([[0.0] * 1536 for _ in batch])

    return all_embeddings


def cluster_logs(parsed_logs):
    """
    Semantic clustering using Azure embeddings + DBSCAN
    """

    if not parsed_logs:
        return []

    messages = [log["message"] for log in parsed_logs]

    # embeddings
    embeddings = get_embeddings(messages)
    embeddings = np.array(embeddings)

    # clustering
    clustering = DBSCAN(
        eps=0.3,
        min_samples=2,
        metric="cosine"
    ).fit(embeddings)

    labels = clustering.labels_

    clusters = defaultdict(list)

    for log, label in zip(parsed_logs, labels):
        clusters[label].append(log)

    result = []

    for label, logs in clusters.items():
        if label == -1:
            result.append({
                "template": "NOISE / UNIQUE EVENTS",
                "count": len(logs),
                "examples": logs[:2],
                "type": "noise"
            })
        else:
            result.append({
                "template": logs[0]["message"],
                "count": len(logs),
                "examples": logs[:2],
                "type": "semantic_cluster"
            })

    result.sort(key=lambda x: x["count"], reverse=True)

    return result