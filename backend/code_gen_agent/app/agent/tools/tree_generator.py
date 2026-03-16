from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import get_llm
from app.agent.schemas.spec import Spec
from app.agent.tools.json_utils import extract_json_from_text


TREE_SYSTEM_PROMPT = """\
You are a senior software architect.

Your task is to design the project structure for a software project.

You must return ONLY valid JSON.

Rules:

1. Return ONLY JSON.
2. No markdown.
3. No explanations.
4. No comments outside JSON.
5. No code blocks.
6. No backticks.

The JSON format must be:

{{
  "tree": [
    "path/to/file1.py",
    "path/to/file2.py"
  ]
}}

Rules for the project structure:

- Include all necessary folders (use __init__.py for Python packages).
- Include starter files (entry points, routers, services, models).
- Include config files (requirements.txt, pyproject.toml, .env.example, etc.).
- Include environment config if the spec requests it.
- Follow the architecture style specified in the spec.
- Do NOT include file contents — only file paths.
"""


def generate_folder_tree(spec: Spec) -> list[str]:
    """
    Stage 1: Generate only the project folder tree via a focused LLM call.
    Returns a list of file paths.
    """
    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", TREE_SYSTEM_PROMPT),
        ("human", "Project specification:\n{spec}"),
    ])

    chain = prompt | llm
    response = chain.invoke({"spec": spec.model_dump()})

    print("----- TREE GENERATOR RAW RESPONSE -----")
    print(response.content)
    print("----- END TREE RESPONSE -----")

    result = extract_json_from_text(response.content)

    if isinstance(result, dict) and "tree" in result:
        return result["tree"]
    elif isinstance(result, list):
        return result

    raise ValueError(f"Unexpected tree response format: {type(result)}")
