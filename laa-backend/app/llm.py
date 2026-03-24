import os
from dotenv import load_dotenv

from langchain_openai import AzureChatOpenAI
from azure.identity import ClientSecretCredential, get_bearer_token_provider
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()


def get_llm():
    """
    Create Azure OpenAI LLM using Azure AD authentication
    (Service Principal: tenant_id, client_id, client_secret)
    """

    credential = ClientSecretCredential(
        tenant_id=os.getenv("AZURE_TENANT_ID"),
        client_id=os.getenv("AZURE_CLIENT_ID"),
        client_secret=os.getenv("AZURE_CLIENT_SECRET"),
    )

    token_provider = get_bearer_token_provider(
        credential,
        "https://cognitiveservices.azure.com/.default"
    )

    llm = AzureChatOpenAI(
        azure_deployment=os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
        azure_ad_token_provider=token_provider,
        temperature=0.2,
    )

    return llm


def generate_summary(anomalies, clusters, stats):
    """
    Generate SRE-style explanation from structured analysis
    """

    if not anomalies:
        return "No significant anomalies detected."

    llm = get_llm()

    SYSTEM_PROMPT = """
You are an expert Site Reliability Engineer (SRE).

You analyze structured log anomaly data and provide:
1. Clear issue explanation
2. Likely root causes
3. Actionable debugging steps
4. Severity level (Low/Medium/High)

Keep the response concise, structured, and practical.
"""

    HUMAN_PROMPT = """
System Analysis Data:

Anomalies:
{anomalies}

Top Clusters:
{clusters}

Statistics:
{stats}

Now analyze and respond.
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", HUMAN_PROMPT),
    ])

    chain = prompt | llm

    try:
        response = chain.invoke({
            "anomalies": anomalies,
            "clusters": clusters,
            "stats": stats,
        })

        return response.content

    except Exception as e:
        return f"LLM Error: {str(e)}"