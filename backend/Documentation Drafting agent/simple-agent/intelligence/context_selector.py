# repo_summarizer/context_selector.py
from typing import Dict, List, Tuple

DEFAULT_MAX_CHARS = 24_000

def select_snippets(file_map: Dict[str, str],
                    ranked_files: List[Tuple[str, float]],
                    max_chars: int = DEFAULT_MAX_CHARS,
                    lines_per_file: int = 120) -> str:
    """
    Build a single string of snippets with separators and stop when max_chars reached.
    ranked_files: list of (path, score) in priority order (best first).
    """
    code_snippets = ""
    total = 0
    for path, _score in ranked_files:
        content = file_map.get(path, "") or ""
        # normalize line endings and pick first N lines
        lines = content.splitlines()[:lines_per_file]
        snippet = f"\n--- File: {path} ---\n" + "\n".join(lines) + "\n"
        if total + len(snippet) > max_chars:
            # try to include truncated tail if some room remains
            remaining = max_chars - total
            if remaining > 100:
                code_snippets += snippet[:remaining]
            break
        code_snippets += snippet
        total += len(snippet)
    return code_snippets