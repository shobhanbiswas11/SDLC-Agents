import subprocess
import os


def run_flake8(repo_path: str):
    """
    Run flake8 on repository and return structured violations.
    """

    result = subprocess.run(
        ["flake8", repo_path],
        capture_output=True,
        text=True
    )

    output = result.stdout.strip()

    if not output:
        return []

    violations = []

    for line in output.split("\n"):
        # flake8 format:
        # path/to/file.py:10:5: E225 missing whitespace around operator

        parts = line.split(":", 3)
        if len(parts) < 4:
            continue

        file_path = parts[0]
        line_number = parts[1]
        column = parts[2]
        message = parts[3].strip()

        violations.append({
            "file_path": file_path,
            "line_number": int(line_number),
            "column": int(column),
            "message": message
        })

    return violations

def extract_snippet(file_path: str, line_number: int, context: int = 5):
    """
    Extract surrounding code for LLM context.
    """

    try:
        with open(file_path, "r") as f:
            lines = f.readlines()

        start = max(line_number - context - 1, 0)
        end = min(line_number + context, len(lines))

        snippet = "".join(lines[start:end])
        return snippet

    except Exception:
        return ""