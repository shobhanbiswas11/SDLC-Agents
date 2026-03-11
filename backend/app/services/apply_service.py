# app/services/apply_service.py

from pathlib import Path


def apply_fix(file_path: str, original_code: str, suggested_code: str):
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"{file_path} not found")

    content = path.read_text()

    if original_code not in content:
        return False

    updated_content = content.replace(original_code, suggested_code, 1)

    path.write_text(updated_content)

    return True
