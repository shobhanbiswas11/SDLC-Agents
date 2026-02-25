import os
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()


def get_llm():
    provider = os.getenv("LLM_PROVIDER", "groq")

    if provider == "groq":
        return ChatOpenAI(
            model="llama-3.1-8b-instant",
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0,
        )

    elif provider == "azure":
        return ChatOpenAI(
            model="gpt-4o",
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            base_url=os.getenv("AZURE_OPENAI_ENDPOINT"),
            temperature=0,
        )

    elif provider == "gemini":
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0,
        )

    else:
        raise ValueError("Unsupported LLM provider")