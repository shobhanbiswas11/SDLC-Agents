# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.output_parsers import JsonOutputParser
# from app.agent.schemas.spec import Spec
# from app.core.llm import get_llm


# def parse_spec_from_text(user_input: str) -> Spec:
#     llm = get_llm()

#     parser = JsonOutputParser(pydantic_object=Spec)

#     prompt = ChatPromptTemplate.from_messages(
#         [
#             (
#                 "system",
#                 """
# You convert free-form software requirements
# into STRICT JSON that matches the provided schema.

# Rules:
# - Return ONLY valid JSON.
# - No markdown.
# - No explanations.
# - No code blocks.
# - No backticks.
# - No additional text.

# If a required field cannot be inferred,
# set it to null.
# """,
#             ),
#             ("human", "{input}"),
#         ]
#     )

#     chain = prompt | llm | parser

#     result = chain.invoke({"input": user_input})

#     print(result)

#     # Ensure we always return a Spec object
#     if isinstance(result, dict):
#         return Spec(**result)

#     return result

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.agent.schemas.spec import Spec
from app.core.llm import get_llm


def parse_spec_from_text(user_input: str) -> Spec:
    llm = get_llm()

    parser = JsonOutputParser(pydantic_object=Spec)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
You are a STRICT specification extractor.

Your job:
Convert user software requirements into a JSON object
that EXACTLY matches the provided schema.

You MUST:
- Return ONLY valid JSON.
- No markdown.
- No explanations.
- No extra text.
- No code blocks.
- No backticks.

If a field is not mentioned,
set it to null.

Schema instructions:
{format_instructions}
""",
            ),
            ("human", "{input}"),
        ]
    )

    chain = prompt | llm | parser

    result = chain.invoke(
        {
            "input": user_input,
            "format_instructions": parser.get_format_instructions(),
        }
    )

    print(result)

    # Guarantee Spec instance
    if isinstance(result, dict):
        return Spec(**result)

    return result