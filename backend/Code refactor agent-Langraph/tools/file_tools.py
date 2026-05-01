"""
tools/file_tools.py — Basic file I/O and workspace navigation tool handlers.

Handlers:
  handle_read_file        — read a local file or remote GitHub blob URL
  handle_write_file       — create or overwrite a local file
  handle_list_files       — list files in a directory (recursive, with skips)
  handle_navigate_to_file — resolve a filename to its workspace-relative path
"""

from __future__ import annotations

from pathlib import Path

from tools._shared import (
    fetch_text_from_url,
    github_blob_to_raw,
    github_session_repo_mismatch_error,
    is_http_url,
    resolve_file_in_workspace,
)
from core.logging import get_logger

logger = get_logger(__name__)

_SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", "venv", ".venv",
    ".refactor_staging", ".refactor_repos",
}
_MAX_FILES = 500


async def handle_read_file(
    file_path: str = "",
    workspace_path: str = ".",
    **kwargs,
) -> dict:
    """Read a local file or fetch a remote GitHub blob URL."""
    # Accept 'path' as an alias (LLM sometimes sends either key)
    if not file_path:
        file_path = kwargs.pop("path", "")
    if not file_path:
        return {"status": "error", "error": "Missing required argument: file_path"}

    if is_http_url(file_path):
        mismatch_error = github_session_repo_mismatch_error(file_path, workspace_path)
        if mismatch_error:
            return {"status": "error", "error": mismatch_error}

        remote_url = github_blob_to_raw(file_path)
        content, fetch_err = fetch_text_from_url(remote_url)
        if fetch_err:
            return {"status": "error", "error": fetch_err}
        return {
            "status": "success",
            "content": content,
            "file_path": remote_url,
            "resolved_path": file_path,
        }

    resolved = resolve_file_in_workspace(file_path, workspace_path)
    if resolved is None:
        return {
            "status": "error",
            "error": f"File not found: '{file_path}' (searched recursively in workspace)",
        }

    # Return workspace-relative path so the frontend can load via /file?path=...
    try:
        rel = str(resolved.relative_to(Path(workspace_path).resolve()))
    except ValueError:
        rel = str(resolved)

    logger.debug("read_file: %s", resolved)
    return {
        "status": "success",
        "content": resolved.read_text(encoding="utf-8"),
        "file_path": str(resolved),
        "resolved_path": rel,
    }


async def handle_write_file(
    file_path: str = "",
    content: str = "",
    workspace_path: str = ".",
    **kwargs,
) -> dict:
    """Write *content* to a local file, creating parent directories as needed."""
    if not file_path:
        file_path = kwargs.pop("path", "")
    if not file_path:
        return {"status": "error", "error": "Missing required argument: file_path"}

    path = (
        Path(file_path)
        if Path(file_path).is_absolute()
        else Path(workspace_path) / file_path
    )
    created = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    try:
        rel = str(path.resolve().relative_to(Path(workspace_path).resolve()))
    except ValueError:
        rel = file_path

    logger.info("write_file: %s (%s)", rel, "created" if created else "updated")
    return {
        "status": "success",
        "message": f"File {'created' if created else 'updated'}: {path}",
        "file_path": rel,   # workspace-relative for frontend navigation
        "created": created,
    }


async def handle_navigate_to_file(
    file_path: str,
    workspace_path: str = ".",
    **_,
) -> dict:
    """Resolve a filename to its workspace-relative path (read-only, for UI navigation)."""
    resolved = resolve_file_in_workspace(file_path, workspace_path)
    if resolved is None:
        return {
            "status": "error",
            "error": f"File not found: '{file_path}' (searched recursively in workspace)",
        }
    try:
        rel = str(resolved.relative_to(Path(workspace_path).resolve()))
    except ValueError:
        rel = str(resolved)

    logger.debug("navigate_to_file: %s", rel)
    return {"status": "success", "resolved_path": rel, "message": f"Navigating to {rel}"}


async def handle_list_files(
    directory: str = ".",
    workspace_path: str = ".",
    **_,
) -> dict:
    """List files recursively in *directory*, skipping known noise directories."""
    path = (
        Path(directory)
        if Path(directory).is_absolute()
        else Path(workspace_path) / directory
    )
    if not path.exists():
        return {"status": "error", "error": f"Directory not found: {path}"}

    files: list[str] = []
    for f in sorted(path.rglob("*")):
        if any(part in _SKIP_DIRS for part in f.parts):
            continue
        if f.is_file():
            files.append(str(f.relative_to(path)))
            if len(files) >= _MAX_FILES:
                break

    result: dict = {"status": "success", "files": files}
    if len(files) >= _MAX_FILES:
        result["note"] = (
            f"Results capped at {_MAX_FILES} files. "
            "Use a subdirectory path for more specific listings."
        )
    return result
