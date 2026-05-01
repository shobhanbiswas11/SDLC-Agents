"""
agent/utils/github_utils.py — GitHub URL parsing and augmentation helpers.

Provides the message augmentation function that appends repository-relative
path hints when the user pastes a GitHub blob URL into their message.
"""

from __future__ import annotations

import re
from urllib.parse import unquote


def augment_message_with_github_paths(message: str, workspace_path: str = ".") -> str:
    """
    If the user's message contains a GitHub blob URL, append a normalised
    repository-relative file-path hint so the agent can call file tools correctly.

    Behaviour differs by session type:
    - GitHub-backed sessions  → prefer the repository-relative path.
    - Local sessions          → instruct the agent to use the full URL directly.

    Args:
        message:        Raw user message text.
        workspace_path: Current workspace root (used to detect GitHub-backed sessions).

    Returns:
        Original message with an optional path-hint block appended.
    """
    pattern = re.compile(
        r"https?://github\.com/[^/\s]+/[^/\s]+/blob/[^/\s]+/(?P<path>[^\s?#]+)"
    )
    matches = list(pattern.finditer(message))
    if not matches:
        return message

    extracted_paths: list[str] = []
    for match in matches:
        path = unquote(match.group("path")).strip().lstrip("/")
        if path and path not in extracted_paths:
            extracted_paths.append(path)

    if not extracted_paths:
        return message

    is_github_backed = ".refactor_repos" in (workspace_path or "")
    hint_lines = ["", "Detected GitHub blob URL(s)."]

    if is_github_backed:
        hint_lines.append(
            "This session is GitHub-backed. Prefer these repository-relative file path(s):"
        )
        hint_lines.extend([f"- {path}" for path in extracted_paths])
    else:
        hint_lines.append(
            "This session is local (not a cloned GitHub workspace). "
            "Use the full GitHub URL directly with read_file/analyze_code. "
            "Do NOT use repository-relative paths in this session."
        )

    return message + "\n" + "\n".join(hint_lines)
