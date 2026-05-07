"""Run flake8 against a repository and parse the results."""
from __future__ import annotations

import re
import subprocess
from typing import List, Tuple

from agents.coding_standards_enforcer.prompts.coding_standards import get_rule_info


def run_flake8(repo_path: str) -> List[dict]:
    """Run flake8 and return a list of structured violation dicts."""
    result = subprocess.run(
        ["flake8", repo_path], capture_output=True, text=True
    )
    output = result.stdout.strip()
    if not output:
        return []

    violations: List[dict] = []
    for line in output.split("\n"):
        # flake8 format:  path/to/file.py:10:5: E225 missing whitespace…
        parts = line.split(":", 3)
        if len(parts) < 4:
            continue

        file_path = parts[0]
        line_number = parts[1]
        column = parts[2]
        message = parts[3].strip()

        rule_code = ""
        rule_match = re.match(r"^([A-Z]\d+)", message)
        if rule_match:
            rule_code = rule_match.group(1)

        rule_info = get_rule_info(rule_code)

        violations.append(
            {
                "file_path": file_path,
                "line_number": int(line_number),
                "column": int(column),
                "message": message,
                "rule_code": rule_code,
                "rule_standard": rule_info["standard"],
                "rule_description": rule_info["description"],
            }
        )

    return violations


def extract_snippet(
    file_path: str, line_number: int, context: int = 5
) -> Tuple[str, int]:
    """Return ±`context` lines around `line_number` plus the snippet's start line."""
    try:
        with open(file_path, "r") as f:
            lines = f.readlines()

        start = max(line_number - context - 1, 0)
        end = min(line_number + context, len(lines))
        snippet = "".join(lines[start:end])
        return snippet, start + 1
    except Exception:
        return "", line_number
