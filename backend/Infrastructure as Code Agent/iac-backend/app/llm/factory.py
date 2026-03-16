#switch logic provider

import os
from .openai_llm import OpenAILLM
from .azure_llm import AzureLLM
from .gemini_llm import GeminiLLM

def get_llm():

    provider = os.getenv("LLM_PROVIDER", "openai").lower()

    if provider == "openai":
        return OpenAILLM()

    if provider == "azure":
        return AzureLLM()

    if provider == "gemini":
        return GeminiLLM()

    raise ValueError("Invalid LLM_PROVIDER. Use openai | azure | gemini")