"""
tools/analysis_tools.py — Code analysis and search tool handlers.

Handlers:
  handle_analyze_code    — read a file and return its content (with AST skeleton
                           for large files) for the ReAct LLM to analyse
  handle_search_code     — full-text / regex search across workspace files
  handle_find_references — find all usages of a symbol across the workspace
"""

from __future__ import annotations

import re
import urllib.parse
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
    ".refactor_staging", ".refactor_repos", ".tox", ".mypy_cache",
}
_BINARY_EXTS = {
    ".pyc", ".pyo", ".so", ".dll", ".exe", ".bin",
    ".png", ".jpg", ".jpeg", ".gif", ".ico",
    ".woff", ".woff2", ".ttf", ".eot",
    ".pdf", ".zip", ".tar", ".gz",
}


# ── AST skeleton helper ────────────────────────────────────────────────────────

def _generate_ast_skeleton(code: str, lang_str: str) -> str | None:
    """
    Use Tree-sitter to produce a structural skeleton of the code.

    Returns a newline-joined string of ``<line_num>: <declaration_line>`` pairs
    for all class / function / interface definitions, or None if Tree-sitter is
    not available or the language is unsupported.
    """
    lang_str = (lang_str or "").lower()
    try:
        if lang_str in ("py", "python"):
            import tree_sitter_python
            from tree_sitter import Language, Parser
            lang = Language(tree_sitter_python.language())
        elif lang_str in ("js", "javascript"):
            import tree_sitter_javascript
            from tree_sitter import Language, Parser
            lang = Language(tree_sitter_javascript.language())
        elif lang_str in ("ts", "typescript", "tsx"):
            import tree_sitter_typescript
            from tree_sitter import Language, Parser
            lang = Language(
                tree_sitter_typescript.language_typescript()
                if lang_str != "tsx"
                else tree_sitter_typescript.language_tsx()
            )
        else:
            return None

        parser = Parser(lang)
        tree = parser.parse(bytes(code, "utf8"))

        target_types = {
            "class_definition", "function_definition",
            "class_declaration", "interface_declaration",
            "function_declaration", "method_definition",
            "lexical_declaration", "type_alias_declaration",
        }

        def _walk(node):
            yield node
            for child in node.children:
                yield from _walk(child)

        line_nums = sorted({
            node.start_point[0]
            for node in _walk(tree.root_node)
            if node.type in target_types
        })

        if not line_nums:
            return None

        code_lines = code.splitlines()
        return "\n".join(f"{r + 1}: {code_lines[r]}" for r in line_nums)

    except Exception as exc:
        logger.debug("AST skeleton generation failed: %s", exc)
        return None


# ── Handlers ───────────────────────────────────────────────────────────────────

async def handle_analyze_code(
    file_path: str,
    language: str = "",
    focus: str = "",
    workspace_path: str = ".",
    **_,
) -> dict:
    """
    Read a file and return its content for the ReAct LLM to analyse.

    For files > 500 lines, a Tree-sitter AST skeleton is returned instead of
    the raw source to avoid token exhaustion.
    """
    resolved_label = file_path

    if is_http_url(file_path):
        mismatch_error = github_session_repo_mismatch_error(file_path, workspace_path)
        if mismatch_error:
            return {"status": "error", "error": mismatch_error}
        remote_url = github_blob_to_raw(file_path)
        code, fetch_err = fetch_text_from_url(remote_url)
        if fetch_err:
            return {"status": "error", "error": fetch_err}
        resolved_label = remote_url
        lang = language or Path(urllib.parse.urlparse(remote_url).path).suffix.lstrip(".")
    else:
        path = resolve_file_in_workspace(file_path, workspace_path)
        if path is None:
            return {
                "status": "error",
                "error": f"File not found: '{file_path}' (searched recursively in workspace)",
            }
        lang = language or path.suffix.lstrip(".")
        code = path.read_text(encoding="utf-8")
        resolved_label = str(path)

    code_lines = code.splitlines()
    total = len(code_lines)

    if total > 500:
        skeleton = _generate_ast_skeleton(code, lang)
        if skeleton:
            numbered = (
                skeleton
                + f"\n\n... (file is {total} lines long. Showing AST structural skeleton only "
                "to save context. If needed, request specific snippets or use suggest_refactor directly.)"
            )
        else:
            numbered = (
                "\n".join(code_lines[:500])
                + f"\n\n... (file truncated — showing first 500 of {total} lines)"
            )
    else:
        numbered = "\n".join(f"{i+1}: {line}" for i, line in enumerate(code_lines))

    return {
        "status": "success",
        "file_path": resolved_label,
        "language": lang,
        "total_lines": total,
        "content": numbered,
        "instruction": (
            f"Analyse this {lang} code for code smells. "
            + (f"Focus on: {focus}. " if focus else "")
            + "Return findings with smell_type, severity (HIGH/MEDIUM/LOW), lines, and description."
        ),
    }


async def handle_search_code(
    query: str,
    file_pattern: str = "*",
    is_regex: bool = False,
    max_results: int = 50,
    workspace_path: str = ".",
    **_,
) -> dict:
    """Search for text or regex patterns across files in the workspace."""
    workspace = Path(workspace_path)
    if not workspace.exists():
        return {"status": "error", "error": f"Workspace not found: {workspace_path}"}

    if is_regex:
        try:
            pattern = re.compile(query)
        except re.error as exc:
            return {"status": "error", "error": f"Invalid regex pattern: {exc}"}
    else:
        pattern = None

    matches: list[dict] = []
    files_searched = 0

    for filepath in sorted(workspace.rglob(file_pattern)):
        if not filepath.is_file():
            continue
        if any(part in _SKIP_DIRS for part in filepath.parts):
            continue
        if filepath.suffix.lower() in _BINARY_EXTS:
            continue

        files_searched += 1
        try:
            text = filepath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for line_num, line in enumerate(text.splitlines(), start=1):
            hit = bool(pattern.search(line)) if pattern else (query in line)
            if hit:
                try:
                    rel_path = str(filepath.relative_to(workspace))
                except ValueError:
                    rel_path = str(filepath)
                matches.append({
                    "file": rel_path,
                    "line": line_num,
                    "content": line.strip()[:200],
                })
                if len(matches) >= max_results:
                    break

        if len(matches) >= max_results:
            break

    return {
        "status": "success",
        "query": query,
        "files_searched": files_searched,
        "total_matches": len(matches),
        "matches": matches,
        "truncated": len(matches) >= max_results,
    }


async def handle_find_references(
    symbol: str,
    file_pattern: str = "*",
    workspace_path: str = ".",
    **_,
) -> dict:
    """
    Find all usages of a symbol (class, function, variable) across the workspace.

    Uses a simple word-boundary regex search — good enough for most refactoring
    use-cases without requiring a full language server.
    """
    if not symbol:
        return {"status": "error", "error": "Missing required argument: symbol"}

    workspace = Path(workspace_path)
    if not workspace.exists():
        return {"status": "error", "error": f"Workspace not found: {workspace_path}"}

    try:
        pattern = re.compile(rf"\b{re.escape(symbol)}\b")
    except re.error as exc:
        return {"status": "error", "error": f"Invalid symbol pattern: {exc}"}

    references: list[dict] = []
    files_searched = 0

    for filepath in sorted(workspace.rglob(file_pattern)):
        if not filepath.is_file():
            continue
        if any(part in _SKIP_DIRS for part in filepath.parts):
            continue
        if filepath.suffix.lower() in _BINARY_EXTS:
            continue

        files_searched += 1
        try:
            text = filepath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for line_num, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                try:
                    rel_path = str(filepath.relative_to(workspace))
                except ValueError:
                    rel_path = str(filepath)
                references.append({
                    "file": rel_path,
                    "line": line_num,
                    "content": line.strip()[:200],
                })
                if len(references) >= 100:
                    break

        if len(references) >= 100:
            break

    return {
        "status": "success",
        "symbol": symbol,
        "files_searched": files_searched,
        "total_references": len(references),
        "references": references,
        "truncated": len(references) >= 100,
    }
