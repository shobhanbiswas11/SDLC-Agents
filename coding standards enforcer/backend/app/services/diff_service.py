import difflib


def generate_diff(original: str, modified: str):
    diff = difflib.unified_diff(
        original.splitlines(),
        modified.splitlines(),
        lineterm=""
    )
    return "\n".join(diff)