from collections import defaultdict
from pathlib import PurePosixPath

from langchain_core.prompts import ChatPromptTemplate
from app.core.llm import get_llm
from app.agent.schemas.spec import Spec
from app.agent.tools.json_utils import extract_json_from_text


CODE_SYSTEM_PROMPT = """\
You are an expert software engineer.

You will generate starter code for multiple files in a project.

You must follow these rules strictly:

1. Return ONLY valid JSON.
2. No explanations.
3. No markdown.
4. No backticks.
5. No text outside JSON.

Output format:

{{
  "files": {{
    "path/to/file.py": "file content as a string",
    "path/to/file2.py": "file content as a string"
  }}
}}

Rules for file content:

- Produce minimal working starter code.
- Follow the architecture defined in the spec.
- Ensure imports are correct and files reference each other correctly.
- Use best practices for the language and framework.
- Include comments where useful.
- Avoid placeholder comments like "implement this later".
- If a file should be empty (like __init__.py), return an empty string "".
- Ensure the code compiles / runs without errors.
"""

MAX_BATCH_SIZE = 5


def batch_files(tree: list[str]) -> list[list[str]]:
    """
    Group files into logical batches by their top-level directory.
    Each batch contains at most MAX_BATCH_SIZE files.
    Root-level files (no directory) are grouped under a special key.
    """
    groups: dict[str, list[str]] = defaultdict(list)

    for path in tree:
        parts = PurePosixPath(path).parts
        # Use the top-level directory as the group key, or "__root__" for
        # files that sit at the project root (e.g. requirements.txt)
        group_key = parts[0] if len(parts) > 1 else "__root__"
        groups[group_key].append(path)

    batches: list[list[str]] = []
    for _key, file_list in groups.items():
        # Split large groups into chunks of MAX_BATCH_SIZE
        for i in range(0, len(file_list), MAX_BATCH_SIZE):
            batches.append(file_list[i : i + MAX_BATCH_SIZE])

    return batches


def generate_code_batch(
    spec: Spec,
    tree: list[str],
    batch: list[str],
) -> dict[str, str]:
    """
    Generate code for a single batch of files via one LLM call.
    """
    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", CODE_SYSTEM_PROMPT),
        (
            "human",
            "Project specification:\n{spec}\n\n"
            "Full project file tree:\n{tree}\n\n"
            "Generate code for ONLY the following files:\n{batch}",
        ),
    ])

    chain = prompt | llm
    response = chain.invoke({
        "spec": spec.model_dump(),
        "tree": "\n".join(tree),
        "batch": "\n".join(batch),
    })

    print(f"----- CODE BATCH RAW RESPONSE (batch: {batch}) -----")
    print(response.content[:500])
    print("----- END CODE BATCH RESPONSE -----")

    result = extract_json_from_text(response.content)

    if isinstance(result, dict) and "files" in result:
        return result["files"]
    elif isinstance(result, dict):
        # The LLM might return the files directly without wrapping
        return result

    raise ValueError(f"Unexpected code batch response format: {type(result)}")


def generate_all_code(spec: Spec, tree: list[str]) -> dict[str, str]:
    """
    Orchestrate batched code generation for the entire project tree.
    Returns a merged dict of {file_path: file_content}.
    """
    batches = batch_files(tree)
    all_files: dict[str, str] = {}

    print(f"[CodeGen] Generating code in {len(batches)} batch(es)...")

    for i, batch in enumerate(batches, 1):
        print(f"[CodeGen] Batch {i}/{len(batches)}: {batch}")
        batch_result = generate_code_batch(spec, tree, batch)
        all_files.update(batch_result)

    return all_files
