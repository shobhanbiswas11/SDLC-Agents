import os
from langchain_google_genai import ChatGoogleGenerativeAI
from .base import BaseLLM

class GeminiLLM(BaseLLM):

    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0,
            google_api_key=os.getenv("GEMINI_API_KEY")
        )

    def generate(self, prompt: str) -> str:
        response = self.llm.invoke(prompt)
        return response.content