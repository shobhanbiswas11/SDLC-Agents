import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from .base import BaseLLM

class OpenAILLM(BaseLLM):

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("human", "{input}")
        ])

    def generate(self, prompt: str) -> str:
        chain = self.prompt | self.llm
        response = chain.invoke({"input": prompt})
        return response.content