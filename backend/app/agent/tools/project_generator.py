from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import get_llm
import json
import re


def extract_json_from_text(text: str):
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:
        json_str = text[start:end+1]
        return json.loads(json_str)

    raise Exception("LLM returned invalid JSON.")

def generate_project_blueprint(spec):
    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages([
    (
    "system",
    """
    You are a senior software architect and backend engineer.

    Your task is to generate a COMPLETE starter project.

    STRICT RULES:

    1. Return ONLY valid JSON.
    2. Do NOT include markdown.
    3. Do NOT include explanations.
    4. Do NOT include code blocks.
    5. Do NOT include backticks.
    6. The JSON must be directly parsable.

    CRITICAL RULE:

    For EVERY file in "tree",
    there MUST be a corresponding entry in "files".

    Example:

    tree:
    [
        "app/main.py",
        "app/api/health.py"
    ]

    files:
    {{
        "app/main.py": "...code...",
        "app/api/health.py": "...code..."
    }}

    NO file from tree may be missing in files.

    If a file is empty (like __init__.py) return "".

    If it is a python module, return minimal working starter code.

    Output JSON format:

    {{
        "tree": ["file/path.py"],
        "files": {{
            "file/path.py": "full starter code"
        }},
        "init_instructions": "step by step instructions to run project"
    }}

    Starter code must:
    - be minimal but functional
    - include imports
    - include example endpoints where needed
    - follow the architecture implied by the spec

    Generate the full project now.
    """
    ),
    ("human", "Project specification:\n{spec}")
    ])

    chain = prompt | llm

    response = chain.invoke({"spec": spec.model_dump()})

    return extract_json_from_text(response.content)