from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import get_llm
from app.agent.schemas.spec import Spec
from app.agent.tools.json_utils import extract_json_from_text


INIT_SYSTEM_PROMPT = """\
You are a senior developer writing setup instructions.

Your task is to generate clear, step-by-step instructions for setting up
and running a software project.

You must return ONLY valid JSON.

Rules:

1. Return ONLY JSON.
2. No markdown.
3. No explanations outside the JSON.
4. No code blocks or backticks.

Output format:

{{
  "init_instructions": "Step-by-step setup instructions as a single string.\\nUse newlines for readability."
}}

The instructions should cover:
- Creating a virtual environment (if applicable)
- Installing dependencies
- Setting up environment variables
- Running the application
- Accessing API docs (if applicable)
"""


def generate_init_instructions(spec: Spec, tree: list[str]) -> str:
    """
    Stage 3: Generate setup/init instructions via a focused LLM call.
    Returns the instructions as a plain string.
    """
    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", INIT_SYSTEM_PROMPT),
        (
            "human",
            "Project specification:\n{spec}\n\n"
            "Project file tree:\n{tree}\n\n"
            "Generate the setup and run instructions.",
        ),
    ])

    chain = prompt | llm
    response = chain.invoke({
        "spec": spec.model_dump(),
        "tree": "\n".join(tree),
    })

    print("----- INIT INSTRUCTIONS RAW RESPONSE -----")
    print(response.content[:300])
    print("----- END INIT RESPONSE -----")

    result = extract_json_from_text(response.content)

    if isinstance(result, dict) and "init_instructions" in result:
        return result["init_instructions"]
    elif isinstance(result, str):
        return result

    raise ValueError(
        f"Unexpected init instructions response format: {type(result)}"
    )
