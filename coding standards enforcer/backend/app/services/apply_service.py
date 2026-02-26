from pathlib import Path


def clean_code_block(code: str) -> str:
    code = code.strip()

    if code.startswith("```"):
        code = code.split("```")[1]

    return code.strip()


def apply_fix(
    file_path: str,
    original_code: str,
    suggested_code: str
):
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"{file_path} not found")

    content = path.read_text()

    suggested_code = clean_code_block(suggested_code)

    if original_code not in content:
        raise ValueError("Original snippet not found in file")

    updated_content = content.replace(original_code, suggested_code, 1)

    path.write_text(updated_content)

    return True