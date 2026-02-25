from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import get_llm


def generate_clarification_questions(missing_fields: list[str]):
    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
Ask concise clarification questions.
Only ask about missing fields.
Maximum 5 questions.
""",
            ),
            ("human", "Missing fields: {fields}"),
        ]
    )

    chain = prompt | llm

    response = chain.invoke({"fields": ", ".join(missing_fields)})

    return response.content