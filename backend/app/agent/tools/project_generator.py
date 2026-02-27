from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import get_llm
import json
import re


def extract_json_from_text(text: str):
    # 1Try direct parse
    try:
        return json.loads(text.strip())
    except Exception:
        pass

    # Try extracting first JSON block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group().strip())
        except Exception:
            pass

    #Debug print if needed
    print("----- LLM RAW RESPONSE -----")
    print(text)
    print("----- END RESPONSE -----")

    raise Exception("LLM returned invalid JSON.")


def generate_project_blueprint(spec):
    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """
You are a software architect.

You MUST:
- Return ONLY valid JSON.
- No markdown.
- No explanations.
- No extra text.
- No code blocks.
- No backticks.

Format:

{{
    "tree": ["file/path.py"],
    "files": {{
        "file/path.py": "code content"
    }},
    "init_instructions": "..."
}}
"""
        ),
        ("human", "Spec:\n{spec}")
    ])

    chain = prompt | llm

    response = chain.invoke({"spec": spec.model_dump()})

    return extract_json_from_text(response.content)