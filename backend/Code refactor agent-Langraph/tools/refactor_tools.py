"""
tools/refactor_tools.py — Core refactoring tool handlers.

Handlers:
  handle_suggest_refactor    — generate SEARCH/REPLACE refactoring blocks via LLM
  handle_apply_refactor      — write staged or provided content back to a file
  handle_diff_preview        — produce a unified diff between original and staged/new content
  handle_multi_refactor      — cross-file search-and-replace with dry-run support
  handle_apply_batch_refactor — apply multiple SEARCH/REPLACE blocks across files in one call
"""

from __future__ import annotations

import difflib
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

from semantic_safety import (
    is_path_protected_by_policy,
    load_refactor_policy,
    validate_semantic_safety,
)
from tools._shared import (
    call_llm,
    is_http_url,
    resolve_blob_url_to_local_file,
    resolve_file_in_workspace,
)
from tools.analysis_tools import _generate_ast_skeleton
from core.logging import get_logger

logger = get_logger(__name__)

_STAGING_DIR_NAME = ".refactor_staging"
_BACKUP_DIR_NAME = "backups"

# ── System prompts ─────────────────────────────────────────────────────────────

_SUGGEST_SYSTEM_PROMPT = (
    "You are a code refactoring expert. You will receive a complete source file.\n"
    "Rules:\n"
    "1. Fix EVERY code smell listed in the instruction — do not skip any.\n"
    "2. Do NOT change public API signatures, return types, or observable behaviour.\n"
    "3. NEVER rename or change localStorage/sessionStorage keys, env var keys, route paths, "
    "auth token names, or cookie/session identifiers.\n"
    "4. Preserve imports unless they are provably unused and removal cannot change runtime behaviour.\n"
    "5. Do NOT change HTTP endpoints, request/response field names, DB/schema field names, "
    "event names, or cache keys.\n"
    "6. Do NOT change authentication/authorization logic, role checks, permission checks, "
    "redirects, or middleware contracts.\n"
    "7. Do NOT add/remove side effects (network calls, storage writes, timers, logging severity, "
    "analytics/telemetry events).\n"
    "8. Preserve framework-specific conventions and runtime assumptions "
    "(React/Next hooks usage, router APIs, SSR/CSR boundaries).\n"
    "9. CRITICAL: NEVER rename classes, functions, or variables that are exported or used by "
    "other files in the codebase (e.g. Pydantic models, variable names like req_data). "
    "This will break the rest of the app!\n"
    "10. Preserve API compatibility: do NOT rename response field keys or change existing "
    "HTTP status-code behavior unless explicitly requested.\n"
    "11. If you extract secrets into environment variables (like os.getenv('SECRET_KEY')), "
    "ALWAYS include a comment: `# WARNING: Update your .env file with this key`.\n"
    "12. Return your changes using SEARCH/REPLACE blocks in this exact format:\n"
    "<<<\n"
    "[exact lines of original code to replace]\n"
    "====\n"
    "[new refactored lines of code]\n"
    ">>>\n"
    "13. You can use multiple SEARCH/REPLACE blocks. Include enough context in the SEARCH "
    "block to uniquely identify the location.\n"
    "14. Keep the same indentation style.\n"
    "15. CRITICAL: If the file is labelled as an 'AST skeleton' because it is too large, "
    "DO NOT write a SEARCH/REPLACE block. Instead, use the ask_user tool to ask the developer "
    "which function/class they want to refactor, or fetch the exact function body first."
)


# ── Internal helpers ───────────────────────────────────────────────────────────

def _staging_file(workspace_path: str, source_path: Path) -> Path:
    staging_dir = Path(workspace_path) / _STAGING_DIR_NAME
    staging_dir.mkdir(exist_ok=True)
    return staging_dir / f"{source_path.stem}_staged{source_path.suffix}"


def _backup_dir(workspace_path: str) -> Path:
    bd = Path(workspace_path) / _STAGING_DIR_NAME / _BACKUP_DIR_NAME
    bd.mkdir(parents=True, exist_ok=True)
    return bd


def _write_refactor_history(workspace_path: str, entry: dict) -> None:
    """Append *entry* to .refactor_history.json (best-effort, never raises)."""
    try:
        history_file = Path(workspace_path) / ".refactor_history.json"
        history: list = []
        if history_file.exists():
            try:
                history = json.loads(history_file.read_text(encoding="utf-8"))
            except Exception:
                history = []
        history.append(entry)
        history_file.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def apply_search_replace_blocks(original_code: str, llm_response: str) -> tuple[str, str | None]:
    """
    Parse ``<<<`` / ``====`` / ``>>>`` blocks from *llm_response* and apply them
    to *original_code*.

    Returns:
        (new_content, error_message_or_None)
    """
    pattern = re.compile(r"<<<[ \t]*\n(.*?)\n====[ \t]*\n(.*?)\n>>>", re.DOTALL)
    blocks = pattern.findall(llm_response)

    if not blocks:
        return original_code, (
            "No SEARCH/REPLACE blocks found in LLM response.\n"
            f"Response was:\n{llm_response}\n"
            "Ensure you use the <<< \\n ... \\n ==== \\n ... \\n >>> format."
        )

    new_content = original_code
    for search_block, replace_block in blocks:
        if search_block not in new_content:
            return new_content, (
                f"Original code block not found in file (must match exactly):\n{search_block[:200]}..."
            )
        new_content = new_content.replace(search_block, replace_block, 1)

    return new_content, None


# ── Handlers ───────────────────────────────────────────────────────────────────

async def handle_suggest_refactor(
    file_path: str,
    smell_type: str,
    description: str = "",
    instruction: str = "",
    lines: str = "",
    workspace_path: str = ".",
    **_,
) -> dict:
    """
    Generate a refactored version that fixes ALL specified code smells in one pass.

    *smell_type* may be a comma-separated list (e.g. ``"magic_numbers,long_method"``).
    Returns the full refactored file content staged for ``apply_refactor``.
    """
    resolution_note = ""
    if is_http_url(file_path):
        resolved_path, resolve_err, note = resolve_blob_url_to_local_file(file_path, workspace_path)
        if resolve_err:
            return {"status": "error", "error": resolve_err}
        path = resolved_path
        resolution_note = note or ""
    else:
        path = resolve_file_in_workspace(file_path, workspace_path)
        if path is None:
            return {
                "status": "error",
                "error": f"File not found: '{file_path}' (searched recursively in workspace)",
            }

    policy = load_refactor_policy(workspace_path)
    if is_path_protected_by_policy(path, workspace_path, policy):
        return {
            "status": "error",
            "error": f"Refactor blocked by policy for protected file: {path}",
            "file_path": str(path),
        }

    full_code = path.read_text(encoding="utf-8")
    total_lines = len(full_code.splitlines())
    smells = [s.strip() for s in smell_type.split(",") if s.strip()]

    # For large files, send only the AST skeleton to save tokens
    lang_hint = path.suffix.lstrip(".")
    if total_lines > 500:
        skeleton = _generate_ast_skeleton(full_code, lang_hint)
        code_payload = (
            f"AST skeleton (file has {total_lines} lines — only signatures shown):\n"
            f"{skeleton}\n\n"
            "NOTE: Your SEARCH blocks must still contain exact original lines from the full file."
        ) if skeleton else full_code
    else:
        code_payload = full_code

    smell_list = ", ".join(smells)
    lines_hint = f"\nAffected lines: {lines}" if lines else ""
    extra_hint = f"\nAdditional instruction: {instruction or description}" if (instruction or description) else ""

    user_msg = (
        f"Fix ALL of these code smells in one complete refactor: {smell_list}"
        f"{lines_hint}{extra_hint}\n\n"
        f"File ({total_lines} lines):\n\n{code_payload}"
    )

    max_tokens = int(os.getenv("REFACTOR_MAX_COMPLETION_TOKENS", "12000"))
    refactored_resp = await call_llm(_SUGGEST_SYSTEM_PROMPT, user_msg, max_tokens=max_tokens)

    if refactored_resp.startswith("[LLM Error:"):
        return {"status": "error", "error": refactored_resp}

    cleaned, block_err = apply_search_replace_blocks(full_code, refactored_resp)
    if block_err:
        return {
            "status": "error",
            "error": f"Failed to apply refactor blocks: {block_err}",
            "file_path": str(path),
            "instruction": "Retry and ensure your SEARCH blocks exactly match the original file text.",
        }

    safety_check = validate_semantic_safety(full_code, cleaned, path.suffix, policy=policy)
    if not safety_check["ok"]:
        return {
            "status": "error",
            "error": "Refactor blocked by semantic safety checks. The proposed change appears to modify behavior-sensitive code.",
            "file_path": str(path),
            "violations": safety_check["violations"],
            "instruction": (
                "Narrow the refactor scope to structural cleanup only "
                "(formatting, extraction, naming of local variables, duplication removal) "
                "without changing storage/env/route/import semantics."
            ),
        }

    # Save to staging so large files aren't truncated in conversation history
    staged = _staging_file(workspace_path, path)
    staged.write_text(cleaned, encoding="utf-8")

    logger.info("suggest_refactor: staged → %s", staged)
    return {
        "status": "success",
        "file_path": str(path),
        "smell_type": smell_list,
        "refactored_snippet": cleaned[:500] + ("\n... [see staged file for full code]" if len(cleaned) > 500 else ""),
        "staging_path": str(staged),
        "lines_affected": lines or f"1-{total_lines}",
        "resolution_note": resolution_note,
        "instruction": (
            "Refactored code is staged. Call diff_preview with new_content='staged' "
            "and then apply_refactor with new_content='staged' to apply it."
        ),
    }


async def handle_diff_preview(
    file_path: str,
    new_content: str = "staged",
    workspace_path: str = ".",
    **_,
) -> dict:
    """Generate a unified diff between the original file and proposed/staged content."""
    if is_http_url(file_path):
        resolved_path, resolve_err, _ = resolve_blob_url_to_local_file(file_path, workspace_path)
        if resolve_err:
            return {"status": "error", "error": resolve_err}
        path = resolved_path
    else:
        path = resolve_file_in_workspace(file_path, workspace_path)
        if path is None:
            return {
                "status": "error",
                "error": f"File not found: '{file_path}' (searched recursively in workspace)",
            }

    if new_content == "staged" or not new_content.strip():
        staged = _staging_file(workspace_path, path)
        if not staged.exists():
            return {"status": "error", "error": "No staged refactoring found. Call suggest_refactor first."}
        new_content = staged.read_text(encoding="utf-8")

    original = path.read_text(encoding="utf-8")
    diff = list(difflib.unified_diff(
        original.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=f"a/{path.name}",
        tofile=f"b/{path.name}",
        lineterm="",
    ))
    diff_text = "\n".join(diff)
    added = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))

    return {
        "status": "success",
        "file_path": str(path),
        "diff": diff_text or "(no changes)",
        "lines_added": added,
        "lines_removed": removed,
    }


async def handle_apply_refactor(
    file_path: str,
    new_content: str = "staged",
    workspace_path: str = ".",
    **_,
) -> dict:
    """
    Write the refactored content to disk.

    Reads staged content when ``new_content='staged'``.
    Creates a backup before overwriting and appends an entry to ``.refactor_history.json``.
    """
    if is_http_url(file_path):
        resolved_path, resolve_err, _ = resolve_blob_url_to_local_file(file_path, workspace_path)
        if resolve_err:
            return {"status": "error", "error": resolve_err}
        path = resolved_path
    else:
        path = resolve_file_in_workspace(file_path, workspace_path)
        if path is None:
            return {
                "status": "error",
                "error": f"File not found: '{file_path}' (searched recursively in workspace)",
            }

    if new_content == "staged" or not new_content.strip():
        staged = _staging_file(workspace_path, path)
        if not staged.exists():
            return {"status": "error", "error": "No staged refactoring found. Call suggest_refactor first."}
        new_content = staged.read_text(encoding="utf-8")
        staged.unlink(missing_ok=True)

    policy = load_refactor_policy(workspace_path)
    if is_path_protected_by_policy(path, workspace_path, policy):
        return {
            "status": "error",
            "error": f"Apply blocked by policy for protected file: {path}",
            "file_path": str(path),
        }

    original_content = path.read_text(encoding="utf-8") if path.exists() else ""
    safety_check = validate_semantic_safety(original_content, new_content, path.suffix, policy=policy)
    if not safety_check["ok"]:
        return {
            "status": "error",
            "error": "Apply blocked by semantic safety checks. No file changes were written.",
            "file_path": str(path),
            "violations": safety_check["violations"],
        }

    path.parent.mkdir(parents=True, exist_ok=True)

    # Backup before overwrite
    backup_path: Path | None = None
    if path.exists():
        backup_path = _backup_dir(workspace_path) / f"{path.stem}_backup{path.suffix}"
        backup_path.write_text(original_content, encoding="utf-8")

    path.write_text(new_content, encoding="utf-8")

    # Diff stats for history
    orig_lines = original_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    diff_lines = list(difflib.unified_diff(orig_lines, new_lines, lineterm=""))
    lines_added = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
    lines_removed = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))

    _write_refactor_history(workspace_path, {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "file_path": str(path),
        "lines_added": lines_added,
        "lines_removed": lines_removed,
        "backup_path": str(backup_path) if backup_path else "",
        "diff_summary": f"+{lines_added} -{lines_removed} lines",
    })

    logger.info("apply_refactor: wrote %s (+%d/-%d lines)", path.name, lines_added, lines_removed)
    return {
        "status": "success",
        "message": f"✅ Refactored code applied to '{path.name}'.",
        "file_path": str(path),
        "source_extension": path.suffix.lower(),
        "backup_path": str(backup_path) if backup_path else "",
    }


async def handle_multi_refactor(
    search_pattern: str,
    replacement: str,
    file_pattern: str = "*",
    dry_run: bool = True,
    workspace_path: str = ".",
    **_,
) -> dict:
    """
    Search and replace a text pattern across multiple files.

    ``dry_run=True`` returns a preview of changes without writing anything.
    ``dry_run=False`` applies changes and creates per-file backups.
    """
    workspace = Path(workspace_path)
    if not workspace.exists():
        return {"status": "error", "error": f"Workspace not found: {workspace_path}"}

    _SKIP = {".git", "node_modules", "__pycache__", "venv", ".venv",
              ".refactor_staging", ".refactor_repos"}
    policy = load_refactor_policy(workspace_path)

    changes: list[dict] = []
    files_affected: set[str] = set()

    for filepath in sorted(workspace.rglob(file_pattern)):
        if not filepath.is_file():
            continue
        if any(part in _SKIP for part in filepath.parts):
            continue
        if is_path_protected_by_policy(filepath, workspace_path, policy):
            continue

        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception:
            continue

        if search_pattern not in content:
            continue

        try:
            rel_path = str(filepath.relative_to(workspace))
        except ValueError:
            rel_path = str(filepath)

        if dry_run:
            for i, line in enumerate(content.splitlines(), 1):
                if search_pattern in line:
                    changes.append({
                        "file": rel_path,
                        "line": i,
                        "before": line.strip()[:150],
                        "after": line.replace(search_pattern, replacement).strip()[:150],
                    })
            files_affected.add(rel_path)
        else:
            new_content = content.replace(search_pattern, replacement)
            backup = _backup_dir(workspace_path) / f"{filepath.stem}_multi_backup_{int(time.time())}{filepath.suffix}"
            backup.write_text(content, encoding="utf-8")
            filepath.write_text(new_content, encoding="utf-8")
            files_affected.add(rel_path)
            _write_refactor_history(workspace_path, {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "file_path": rel_path,
                "type": "multi_refactor",
                "search": search_pattern,
                "replacement": replacement,
                "backup_path": str(backup),
            })

    return {
        "status": "success",
        "dry_run": dry_run,
        "search_pattern": search_pattern,
        "replacement": replacement,
        "files_affected_count": len(files_affected),
        "files_affected": sorted(files_affected),
        "changes_preview": changes if dry_run else [],
        "message": (
            f"Successfully {'previewed' if dry_run else 'applied'} replacement "
            f"across {len(files_affected)} files."
        ),
    }


async def handle_apply_batch_refactor(
    file_path: str,
    blocks: list[dict],
    workspace_path: str = ".",
    **_,
) -> dict:
    """
    Apply multiple SEARCH/REPLACE operations to a file in a single call.

    *blocks* is a list of ``{"search": "...", "replace": "..."}`` dicts.
    This avoids the LLM having to call ``suggest_refactor`` + ``apply_refactor``
    for simple targeted changes.
    """
    if not blocks:
        return {"status": "error", "error": "No replacement blocks provided."}

    path = resolve_file_in_workspace(file_path, workspace_path)
    if path is None:
        return {
            "status": "error",
            "error": f"File not found: '{file_path}' (searched recursively in workspace)",
        }

    policy = load_refactor_policy(workspace_path)
    if is_path_protected_by_policy(path, workspace_path, policy):
        return {
            "status": "error",
            "error": f"Apply blocked by policy for protected file: {path}",
        }

    content = path.read_text(encoding="utf-8")
    applied = 0
    errors: list[str] = []

    for i, block in enumerate(blocks):
        search = block.get("search", "")
        replace = block.get("replace", "")
        if not search:
            errors.append(f"Block {i}: missing 'search' key")
            continue
        if search not in content:
            errors.append(f"Block {i}: search text not found in file")
            continue
        content = content.replace(search, replace, 1)
        applied += 1

    if errors and applied == 0:
        return {"status": "error", "error": "; ".join(errors)}

    # Backup and write
    backup: Path | None = None
    original = path.read_text(encoding="utf-8")
    if path.exists():
        backup = _backup_dir(workspace_path) / f"{path.stem}_batch_backup{path.suffix}"
        backup.write_text(original, encoding="utf-8")

    path.write_text(content, encoding="utf-8")
    logger.info("apply_batch_refactor: applied %d/%d blocks to %s", applied, len(blocks), path.name)

    result: dict = {
        "status": "success",
        "message": f"Applied {applied}/{len(blocks)} replacement blocks to '{path.name}'.",
        "file_path": str(path),
        "blocks_applied": applied,
        "backup_path": str(backup) if backup else "",
    }
    if errors:
        result["warnings"] = errors
    return result
