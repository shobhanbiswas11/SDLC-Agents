"""
tools.py — All tool handler functions for the Code Refactoring Agent.

Tool schemas are loaded from config/tools/*.yaml by config_loader.py.
This file contains the Python handler functions that execute the tools.
The AI decides which tool to call, we look it up in TOOL_HANDLERS, and run it.
"""

import os
import json
import difflib
import subprocess
import shutil
import base64
import re
import urllib.request
import urllib.parse
import urllib.error
import hashlib
from pathlib import Path

from semantic_safety import (
    is_path_protected_by_policy,
    load_refactor_policy,
    validate_semantic_safety,
)


# ──────────────────────────────────────────────
# LLM HELPER
# ──────────────────────────────────────────────

import time as _time

_tools_cached_client = None
_tools_cached_client_time = 0.0
_TOOLS_CLIENT_TTL = 1800  # 30 min


def _extract_first_http_url(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    match = re.search(r"https?://\S+", text)
    if not match:
        return ""
    return match.group(0).strip("'\"),.;>]")


def _is_http_url(value: str) -> bool:
    parsed = urllib.parse.urlparse(_normalize_url_candidate(value))
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _normalize_url_candidate(value: str) -> str:
    """
    Normalize pasted URL-like inputs that may include trailing punctuation
    or extra text (timestamps, labels).
    """
    text = (value or "").strip()
    if not text:
        return ""
    embedded = _extract_first_http_url(text)
    if embedded:
        return embedded

    github_match = re.search(r"(?:^|\s)((?:www\.)?github\.com/\S+)", text)
    if github_match:
        candidate = github_match.group(1).strip("'\"),.;>]")
        return "https://" + candidate

    first_token = text.split()[0]
    if first_token.startswith("github.com/") or first_token.startswith("www.github.com/"):
        first_token = f"https://{first_token}"
    return first_token.strip("'\"),.;>]")


def _github_blob_to_raw(url: str) -> str:
    """Convert a GitHub blob URL to raw content URL; return input if unchanged."""
    normalized = _normalize_url_candidate(url)
    parsed = urllib.parse.urlparse(normalized)
    if parsed.netloc not in {"github.com", "www.github.com"}:
        return url

    parts = [p for p in parsed.path.split("/") if p]
    # /<owner>/<repo>/blob/<branch>/<path...>
    if len(parts) >= 5 and parts[2] == "blob":
        owner, repo, _, branch = parts[:4]
        file_path = "/".join(parts[4:])
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"

    return url


def _github_blob_repo_and_path(url: str) -> tuple[str, str] | None:
    """Return (repo_url, repo_relative_path) for GitHub blob URL, else None."""
    normalized = _normalize_url_candidate(url)
    parsed = urllib.parse.urlparse(normalized)
    if parsed.netloc not in {"github.com", "www.github.com"}:
        return None

    parts = [p for p in parsed.path.split("/") if p]
    # /<owner>/<repo>/blob/<branch>/<path...>
    if len(parts) >= 5 and parts[2] == "blob":
        owner, repo, _, _branch = parts[:4]
        file_path = "/".join(parts[4:])
        return (f"https://github.com/{owner}/{repo}", file_path)
    return None


def _github_blob_parts(url: str) -> tuple[str, str, str] | None:
    """Return (repo_url, branch, repo_relative_path) for GitHub blob URL."""
    normalized = _normalize_url_candidate(url)
    parsed = urllib.parse.urlparse(normalized)
    if parsed.netloc not in {"github.com", "www.github.com"}:
        return None

    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 5 or parts[2] != "blob":
        return None

    owner, repo, _, branch = parts[:4]
    repo_rel_path = "/".join(parts[4:])
    if not repo_rel_path:
        return None
    return (f"https://github.com/{owner}/{repo}", branch, repo_rel_path)


def _normalize_github_repo_url(repo_url: str) -> str:
    raw = (repo_url or "").strip()
    if not raw:
        return ""

    if raw.startswith("git@github.com:"):
        raw = "https://github.com/" + raw.split("git@github.com:", 1)[1]

    parsed = urllib.parse.urlparse(raw if "://" in raw else f"https://{raw}")
    if parsed.netloc not in {"github.com", "www.github.com"}:
        return ""

    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        return ""

    owner = parts[0]
    repo = parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    return f"https://github.com/{owner}/{repo}"


def _workspace_github_repo_url(workspace_path: str) -> str:
    """Best-effort read of the current workspace git origin as normalized GitHub repo URL."""
    workspace = Path(workspace_path)
    if not workspace.exists():
        return ""

    try:
        result = subprocess.run(
            ["git", "-C", str(workspace), "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0:
            return ""
        return _normalize_github_repo_url(result.stdout.strip())
    except Exception:
        return ""


def _github_session_repo_mismatch_error(file_path: str, workspace_path: str) -> str | None:
    """
    In GitHub-backed sessions, detect when a blob URL points to a different repo than the cloned workspace.
    Returns a user-facing error string when mismatch is detected.
    """
    if ".refactor_repos" not in (workspace_path or ""):
        return None

    blob_info = _github_blob_repo_and_path(file_path)
    if not blob_info:
        return None

    requested_repo, requested_rel_path = blob_info
    current_repo = _workspace_github_repo_url(workspace_path)
    if not current_repo:
        return None

    # Defensive fallback: if the requested repo-relative file already exists in this
    # GitHub-backed workspace, treat it as same-session and do not raise mismatch.
    try:
        candidate = Path(workspace_path) / requested_rel_path
        if candidate.exists() and candidate.is_file():
            return None
    except Exception:
        pass

    if _normalize_github_repo_url(requested_repo) == _normalize_github_repo_url(current_repo):
        return None

    return (
        "GitHub session repository mismatch detected. "
        f"Current session repo: {current_repo}. "
        f"Requested file repo: {requested_repo} (path: {requested_rel_path}). "
        "Start a NEW workflow with source_type='github' and github_url set to the requested repo, "
        "then use repository-relative file paths in that new session."
    )


def _is_safe_repo_relative_path(repo_path: str) -> bool:
    text = (repo_path or "").strip().replace("\\", "/")
    if not text or text.startswith("/"):
        return False
    parts = [part for part in text.split("/") if part not in {"", "."}]
    return all(part != ".." for part in parts)


def _clone_repo_if_needed(repo_url: str, branch: str, clone_path: Path) -> tuple[bool, str | None]:
    """Ensure a repo exists at clone_path. Returns (ok, error)."""
    try:
        if (clone_path / ".git").exists():
            origin = _workspace_github_repo_url(str(clone_path))
            if _normalize_github_repo_url(origin) == _normalize_github_repo_url(repo_url):
                return True, None
            shutil.rmtree(clone_path, ignore_errors=True)

        clone_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["git", "clone", "--depth", "1", "--branch", branch, repo_url, str(clone_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "Unknown git clone error").strip()
            return False, f"Failed to auto-clone repository: {err}"
        return True, None
    except subprocess.TimeoutExpired:
        return False, "Failed to auto-clone repository: git clone timed out after 120 seconds."
    except Exception as e:
        return False, f"Failed to auto-clone repository: {str(e)}"


def _resolve_blob_url_to_local_file(file_path: str, workspace_path: str) -> tuple[Path | None, str | None, str | None]:
    """
    Resolve GitHub blob URL to a local file path.
    Returns (resolved_path, error, note).
    - In GitHub-backed session: maps same-repo blob URL to workspace-relative file.
    - In local session: auto-clones repo to ad-hoc cache and resolves file path.
    """
    parts = _github_blob_parts(file_path)
    if not parts:
        return None, "Only GitHub blob URLs are supported for this operation.", None

    repo_url, branch, repo_rel_path = parts
    if not _is_safe_repo_relative_path(repo_rel_path):
        return None, "Unsafe repository file path detected in URL.", None

    is_github_backed = ".refactor_repos" in (workspace_path or "")
    if is_github_backed:
        mismatch_error = _github_session_repo_mismatch_error(file_path, workspace_path)
        if mismatch_error:
            return None, mismatch_error, None

        resolved = Path(workspace_path) / repo_rel_path
        if not resolved.exists():
            return None, f"File not found in current GitHub-backed workspace: {resolved}", None
        return resolved, None, "Mapped GitHub blob URL to current session workspace file."

    repo_key = hashlib.sha1(f"{_normalize_github_repo_url(repo_url)}@{branch}".encode("utf-8")).hexdigest()[:12]
    clone_root = Path(__file__).resolve().parent / ".refactor_repos" / "adhoc"
    clone_path = clone_root / f"repo-{repo_key}"

    ok, clone_err = _clone_repo_if_needed(repo_url, branch, clone_path)
    if not ok:
        return None, clone_err, None

    resolved = clone_path / repo_rel_path
    if not resolved.exists():
        return None, f"File not found in auto-cloned repository: {repo_rel_path}", None

    return resolved, None, (
        "Auto-cloned GitHub repository for refactor workflow fallback in local session. "
        f"Workspace: {clone_path}"
    )


def _fetch_text_from_url(url: str, timeout: int = 20) -> tuple[str | None, str | None]:
    """Fetch UTF-8 text from URL. Returns (content, error)."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "refactor-agent"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode("utf-8")
            return content, None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code} while fetching URL: {url}"
    except urllib.error.URLError as e:
        return None, f"Network error while fetching URL: {e.reason}"
    except UnicodeDecodeError:
        return None, "Remote file is not UTF-8 text."
    except Exception as e:
        return None, f"Failed to fetch URL: {str(e)}"


def _get_tools_llm_client():
    """Build or return a cached Azure OpenAI client for tool-internal LLM calls."""
    global _tools_cached_client, _tools_cached_client_time

    if _tools_cached_client and (_time.time() - _tools_cached_client_time) < _TOOLS_CLIENT_TTL:
        return _tools_cached_client

    from openai import AzureOpenAI
    from azure.identity import ClientSecretCredential

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
    tenant_id = os.getenv("AZURE_TENANT_ID", "")
    client_id = os.getenv("AZURE_CLIENT_ID", "")
    client_secret = os.getenv("AZURE_CLIENT_SECRET", "")

    if tenant_id and client_id and client_secret:
        cred = ClientSecretCredential(tenant_id, client_id, client_secret)
        token_obj = cred.get_token("https://cognitiveservices.azure.com/.default")
        client = AzureOpenAI(azure_endpoint=endpoint, api_version=api_version, api_key=token_obj.token)
    else:
        client = AzureOpenAI(azure_endpoint=endpoint, api_version=api_version, api_key=os.getenv("AZURE_OPENAI_API_KEY", ""))

    _tools_cached_client = client
    _tools_cached_client_time = _time.time()
    return client


def _call_llm(system_msg: str, user_msg: str, max_tokens: int = 4096) -> str:
    """Call Azure OpenAI for refactoring analysis. Returns the LLM text."""
    client = _get_tools_llm_client()
    deployment = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_completion_tokens=max_tokens,
            timeout=90,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        return f"[LLM Error: {str(e)}]"


def _looks_truncated_refactor(original: str, candidate: str, file_suffix: str) -> bool:
    """Heuristic guard to detect suspiciously incomplete full-file refactors."""
    original_lines = len(original.splitlines())
    candidate_lines = len(candidate.splitlines())

    if not candidate.strip():
        return True

    if original_lines >= 40 and candidate_lines < max(20, int(original_lines * 0.55)):
        return True

    # For common source files, a one-line/very short replacement is almost always truncation.
    source_suffixes = {
        ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rb", ".php", ".cs", ".cpp", ".c"
    }
    if file_suffix.lower() in source_suffixes and original_lines >= 20 and candidate_lines <= 5:
        return True

    # Abrupt cutoffs often end with unfinished tokens.
    tail = candidate.rstrip()[-80:]
    suspicious_tails = ("...", "```", "return", "const", "function", "class", "if (")
    if any(tail.endswith(tok) for tok in suspicious_tails) and candidate_lines < original_lines:
        return True

    return False


def _extract_quoted_tokens(text: str) -> list[str]:
    return re.findall(r"'([^']+)'|\"([^\"]+)\"", text)


def _flatten_quoted_tokens(matches: list[tuple[str, str]]) -> list[str]:
    tokens: list[str] = []
    for a, b in matches:
        value = a or b
        if value:
            tokens.append(value)
    return tokens


def _tokens_from_semantic_violations(violations: list[str]) -> list[str]:
    raw = "\n".join(violations or [])
    matches = _extract_quoted_tokens(raw)
    tokens = _flatten_quoted_tokens(matches)
    seen: set[str] = set()
    ordered: list[str] = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            ordered.append(token)
    return ordered[:60]


# ──────────────────────────────────────────────
# REFACTORING TOOL HANDLERS
# ──────────────────────────────────────────────

async def handle_analyze_code(file_path: str, language: str = "", focus: str = "", workspace_path: str = ".", **_) -> dict:
    """
    Read a file and return its content for the ReAct LLM to analyze.
    No internal LLM call — the orchestrator LLM does the analysis directly.
    """
    resolved_label = file_path
    if _is_http_url(file_path):
        mismatch_error = _github_session_repo_mismatch_error(file_path, workspace_path)
        if mismatch_error:
            return {"status": "error", "error": mismatch_error}

        remote_url = _github_blob_to_raw(file_path)
        code, fetch_err = _fetch_text_from_url(remote_url)
        if fetch_err:
            return {"status": "error", "error": fetch_err}
        resolved_label = remote_url
        lang = language or Path(urllib.parse.urlparse(remote_url).path).suffix.lstrip(".")
    else:
        path = Path(file_path) if Path(file_path).is_absolute() else Path(workspace_path) / file_path
        if not path.exists():
            return {"status": "error", "error": f"File not found: {path}"}
        code = path.read_text(encoding="utf-8")
        lang = language or path.suffix.lstrip(".")
        resolved_label = str(path)

    # For very large files, only send the first 500 lines
    code_lines = code.splitlines()
    total = len(code_lines)
    if total > 500:
        code = "\n".join(code_lines[:500])
        code += f"\n\n... (file truncated — showing first 500 of {total} lines)"

    # Add line numbers so the LLM can reference specific lines
    numbered = "\n".join(f"{i+1}: {line}" for i, line in enumerate(code.splitlines()))

    return {
        "status": "success",
        "file_path": resolved_label,
        "language": lang,
        "total_lines": total,
        "content": numbered,
        "instruction": f"Analyze this {lang} code for code smells. " + (f"Focus on: {focus}. " if focus else "") +
                       "Return findings with smell_type, severity (HIGH/MEDIUM/LOW), lines, and description.",
    }


async def handle_suggest_refactor(file_path: str, smell_type: str, description: str = "", instruction: str = "", lines: str = "", workspace_path: str = ".", **_) -> dict:
    """
    Generate a refactored version that fixes ALL specified code smells in one pass.
    smell_type may be a comma-separated list (e.g. "magic_numbers,duplicate_code,long_method").
    Returns the full refactored file content ready for apply_refactor.
    """
    resolution_note = ""
    if _is_http_url(file_path):
        resolved_path, resolve_err, note = _resolve_blob_url_to_local_file(file_path, workspace_path)
        if resolve_err:
            return {"status": "error", "error": resolve_err}
        path = resolved_path
        resolution_note = note or ""
    else:
        path = Path(file_path) if Path(file_path).is_absolute() else Path(workspace_path) / file_path

    if not path.exists():
        return {"status": "error", "error": f"File not found: {path}"}

    policy = load_refactor_policy(workspace_path)
    if is_path_protected_by_policy(path, workspace_path, policy):
        return {
            "status": "error",
            "error": f"Refactor blocked by policy for protected file: {path}",
            "file_path": str(path),
        }

    full_code = path.read_text(encoding="utf-8")
    total_lines = len(full_code.splitlines())

    # Parse smell list — always send the full file so no context is lost
    smells = [s.strip() for s in smell_type.split(",") if s.strip()]

    system_msg = (
        "You are a code refactoring expert. You will receive a complete source file.\n"
        "Rules:\n"
        "1. Fix EVERY code smell listed in the instruction — do not skip any.\n"
        "2. Do NOT change public API signatures, return types, or observable behaviour.\n"
        "3. NEVER rename or change localStorage/sessionStorage keys, env var keys, route paths, auth token names, or cookie/session identifiers.\n"
        "4. Preserve imports unless they are provably unused and removal cannot change runtime behaviour.\n"
        "5. Do NOT change HTTP endpoints, request/response field names, DB/schema field names, event names, or cache keys.\n"
        "6. Do NOT change authentication/authorization logic, role checks, permission checks, redirects, or middleware contracts.\n"
        "7. Do NOT add/remove side effects (network calls, storage writes, timers, logging severity, analytics/telemetry events).\n"
        "8. Preserve framework-specific conventions and runtime assumptions (React/Next hooks usage, router APIs, SSR/CSR boundaries).\n"
        "9. Keep function/class/module names and exported symbol names unchanged unless a rename is explicitly requested in the instruction.\n"
        "10. Preserve API compatibility: do NOT rename response field keys or change existing HTTP status-code behavior unless explicitly requested.\n"
        "11. Prefer minimal, localized edits; avoid broad rewrites of unaffected sections.\n"
        "12. Return ONLY the complete refactored file — no line numbers, no explanations, no markdown fences.\n"
        "13. Keep the same indentation style."
    )

    smell_list = ", ".join(smells)
    lines_hint = f"\nAffected lines: {lines}" if lines else ""
    extra_hint = f"\nAdditional instruction: {instruction or description}" if (instruction or description) else ""
    user_msg = (
        f"Fix ALL of these code smells in one complete refactor: {smell_list}"
        f"{lines_hint}{extra_hint}\n\n"
        f"Complete file ({total_lines} lines):\n\n{full_code}"
    )

    max_tokens = int(os.getenv("REFACTOR_MAX_COMPLETION_TOKENS", "12000"))
    refactored = _call_llm(system_msg, user_msg, max_tokens=max_tokens)

    # Strip markdown fences if present
    cleaned = refactored.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]

    if cleaned.startswith("[LLM Error:"):
        return {
            "status": "error",
            "error": cleaned,
        }

    if _looks_truncated_refactor(full_code, cleaned, path.suffix):
        return {
            "status": "error",
            "error": (
                "Refactor output appears truncated/incomplete. No changes were staged. "
                "Please retry with a narrower scope or raise REFACTOR_MAX_COMPLETION_TOKENS."
            ),
            "file_path": str(path),
            "original_lines": total_lines,
            "candidate_lines": len(cleaned.splitlines()),
        }

    safety_check = validate_semantic_safety(full_code, cleaned, path.suffix, policy=policy)
    safe_retry_used = False
    if not safety_check["ok"]:
        # One automatic retry with stricter immutable-token constraints.
        immutable_tokens = _tokens_from_semantic_violations(safety_check.get("violations", []))
        retry_system_msg = (
            system_msg
            + "\n14. STRICT MODE: You must preserve behavior-sensitive literals exactly."
            + "\n15. Do not alter any token in the IMMUTABLE TOKENS list."
            + "\n16. If uncertain, keep original code for that section unchanged."
        )
        retry_user_msg = (
            f"Previous refactor violated semantic safety checks: {safety_check['violations']}.\n"
            f"IMMUTABLE TOKENS: {immutable_tokens}.\n"
            "Retry with structural-only refactor (readability, small extraction, dead-code cleanup) "
            "while preserving ALL behavior-sensitive literals and API contracts.\n\n"
            f"Complete file ({total_lines} lines):\n\n{full_code}"
        )

        retried = _call_llm(retry_system_msg, retry_user_msg, max_tokens=max_tokens).strip()
        if retried.startswith("```"):
            retried = retried.split("\n", 1)[1].rsplit("```", 1)[0]

        if retried and not retried.startswith("[LLM Error:") and not _looks_truncated_refactor(full_code, retried, path.suffix):
            retry_safety = validate_semantic_safety(full_code, retried, path.suffix, policy=policy)
            if retry_safety["ok"]:
                cleaned = retried
                safety_check = retry_safety
                safe_retry_used = True
            else:
                safety_check = retry_safety

    if not safety_check["ok"]:
        return {
            "status": "error",
            "error": (
                "Refactor blocked by semantic safety checks even after a stricter safe retry. "
                "The proposed change appears to modify behavior-sensitive code."
            ),
            "file_path": str(path),
            "violations": safety_check["violations"],
            "safe_retry_used": True,
            "instruction": (
                "Narrow the refactor scope to structural cleanup only "
                "(formatting, extraction, naming of local variables, duplication removal) "
                "without changing storage/env/route/import semantics."
            ),
        }

    new_content = cleaned

    # Save to staging file so it doesn't get truncated in conversation history
    staging_dir = Path(workspace_path) / ".refactor_staging"
    staging_dir.mkdir(exist_ok=True)
    staging_file = staging_dir / f"{path.stem}_staged{path.suffix}"
    staging_file.write_text(new_content, encoding="utf-8")

    return {
        "status": "success",
        "file_path": str(path),
        "smell_type": smell_list,
        "refactored_snippet": cleaned[:500] + ("\n... [see staged file for full code]" if len(cleaned) > 500 else ""),
        "staging_path": str(staging_file),
        "lines_affected": lines or f"1-{total_lines}",
        "resolution_note": resolution_note,
        "safe_retry_used": safe_retry_used,
        "instruction": "Refactored code is staged. Call diff_preview with new_content='staged' and then apply_refactor with new_content='staged' to apply it.",
    }


async def handle_diff_preview(file_path: str, new_content: str = "staged", workspace_path: str = ".", **_) -> dict:
    """
    Generate a unified diff between the original file and proposed new content.
    If new_content is 'staged', reads from the staging file created by suggest_refactor.
    """
    if _is_http_url(file_path):
        resolved_path, resolve_err, _ = _resolve_blob_url_to_local_file(file_path, workspace_path)
        if resolve_err:
            return {"status": "error", "error": resolve_err}
        path = resolved_path
    else:
        path = Path(file_path) if Path(file_path).is_absolute() else Path(workspace_path) / file_path

    if not path.exists():
        return {"status": "error", "error": f"File not found: {path}"}

    # If 'staged', read refactored content from the staging file
    if new_content == "staged" or not new_content.strip():
        staging_file = Path(workspace_path) / ".refactor_staging" / f"{path.stem}_staged{path.suffix}"
        if not staging_file.exists():
            return {"status": "error", "error": "No staged refactoring found. Call suggest_refactor first."}
        new_content = staging_file.read_text(encoding="utf-8")

    original = path.read_text(encoding="utf-8")
    original_lines = original.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff = difflib.unified_diff(
        original_lines,
        new_lines,
        fromfile=f"a/{path.name}",
        tofile=f"b/{path.name}",
        lineterm="",
    )
    diff_text = "\n".join(diff)

    # Count additions and deletions
    added = sum(1 for line in diff_text.split("\n") if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff_text.split("\n") if line.startswith("-") and not line.startswith("---"))

    return {
        "status": "success",
        "file_path": str(path),
        "diff": diff_text or "(no changes)",
        "lines_added": added,
        "lines_removed": removed,
    }


async def handle_apply_refactor(file_path: str, new_content: str = "staged", workspace_path: str = ".", **_) -> dict:
    """
    Apply refactored code by writing it to the file.
    If new_content is 'staged', reads from the staging file created by suggest_refactor.
    Should only be called after user approval.
    """
    if _is_http_url(file_path):
        resolved_path, resolve_err, _ = _resolve_blob_url_to_local_file(file_path, workspace_path)
        if resolve_err:
            return {"status": "error", "error": resolve_err}
        path = resolved_path
    else:
        path = Path(file_path) if Path(file_path).is_absolute() else Path(workspace_path) / file_path

    # If 'staged', read refactored content from the staging file
    if new_content == "staged" or not new_content.strip():
        staging_file = Path(workspace_path) / ".refactor_staging" / f"{path.stem}_staged{path.suffix}"
        if not staging_file.exists():
            return {"status": "error", "error": "No staged refactoring found. Call suggest_refactor first."}
        new_content = staging_file.read_text(encoding="utf-8")
        # Clean up staging file
        staging_file.unlink(missing_ok=True)

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

    backup_path = None
    if path.exists():
        backup_dir = Path(workspace_path) / ".refactor_staging" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"{path.stem}_backup{path.suffix}"
        backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    path.write_text(new_content, encoding="utf-8")
    return {
        "status": "success",
        "message": f"✅ Refactored code applied to '{path.name}'.",
        "file_path": str(path),
        "source_extension": path.suffix.lower(),
        "backup_path": str(backup_path) if backup_path else "",
    }


async def handle_run_tests(test_command: str = "pytest", test_path: str = "", source_file: str = "", workspace_path: str = ".", **_) -> dict:
    """
    Run tests for the refactored file when possible.
    If no dedicated tests are found, fall back to a syntax check for that source file.
    """
    workspace = Path(workspace_path)
    resolved_source: Path | None = None

    if source_file:
        source_path = Path(source_file)
        resolved_source = source_path if source_path.is_absolute() else workspace / source_path

    if not test_path and resolved_source is not None:
        stem = resolved_source.stem
        source_parent = resolved_source.parent
        candidates = [
            workspace / "tests" / f"test_{stem}.py",
            source_parent / f"test_{stem}.py",
            workspace / "sample_code" / f"test_{stem}.py",
        ]
        for candidate in candidates:
            if candidate.exists():
                test_path = str(candidate.relative_to(workspace)) if candidate.is_absolute() else str(candidate)
                break

    if not test_path and resolved_source is not None:
        suffix = resolved_source.suffix.lower()
        syntax_cmd: list[str] | None = None
        checker_name = ""

        if suffix == ".py":
            syntax_cmd = ["python", "-m", "py_compile", str(resolved_source)]
            checker_name = "python -m py_compile"
        elif suffix in {".js", ".mjs", ".cjs"}:
            node_path = shutil.which("node")
            if node_path:
                syntax_cmd = [node_path, "--check", str(resolved_source)]
                checker_name = "node --check"

        if syntax_cmd is None:
            return {
                "status": "success",
                "passed": False,
                "return_code": 0,
                "stdout": "",
                "stderr": "",
                "test_path": "",
                "source_file": str(resolved_source),
                "used_syntax_check": False,
                "message": f"⚠️ No dedicated tests were found, and no syntax checker is configured for '{suffix or 'unknown'}' files in this environment.",
            }

        try:
            result = subprocess.run(
                syntax_cmd,
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=120,
            )
            passed = result.returncode == 0
            stderr_tail = (result.stderr or "").strip()[-300:]
            return {
                "status": "success",
                "passed": passed,
                "return_code": result.returncode,
                "stdout": result.stdout[-3000:] if result.stdout else "",
                "stderr": result.stderr[-1000:] if result.stderr else "",
                "test_path": "",
                "source_file": str(resolved_source),
                "used_syntax_check": True,
                "message": (
                    f"⚠️ No dedicated tests were found. Fallback syntax check ({checker_name}) passed."
                    if passed
                    else f"❌ No dedicated tests were found and fallback syntax check ({checker_name}) failed."
                    + (f" Error: {stderr_tail}" if stderr_tail else "")
                ),
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "Syntax check timed out after 120 seconds."}
        except Exception as e:
            return {"status": "error", "error": f"Failed to run syntax check: {str(e)}"}

    cmd = test_command
    if test_path:
        cmd = f"{cmd} {test_path}"

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=workspace_path,
            capture_output=True,
            text=True,
            timeout=120,
        )
        passed = result.returncode == 0
        return {
            "status": "success",
            "passed": passed,
            "return_code": result.returncode,
            "stdout": result.stdout[-3000:] if result.stdout else "",
            "stderr": result.stderr[-1000:] if result.stderr else "",
            "test_path": test_path,
            "source_file": str(resolved_source) if resolved_source else "",
            "used_syntax_check": False,
            "message": "✅ All tests passed!" if passed else "❌ Some tests failed.",
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "Test command timed out after 120 seconds."}
    except Exception as e:
        return {"status": "error", "error": f"Failed to run tests: {str(e)}"}


# ──────────────────────────────────────────────
# BASIC FILE TOOL HANDLERS
# ──────────────────────────────────────────────

async def handle_read_file(file_path: str, workspace_path: str = ".", **_) -> dict:
    """Read a local file or remote GitHub URL."""
    if _is_http_url(file_path):
        mismatch_error = _github_session_repo_mismatch_error(file_path, workspace_path)
        if mismatch_error:
            return {"status": "error", "error": mismatch_error}

        remote_url = _github_blob_to_raw(file_path)
        content, fetch_err = _fetch_text_from_url(remote_url)
        if fetch_err:
            return {"status": "error", "error": fetch_err}
        return {"status": "success", "content": content, "file_path": remote_url}

    path = Path(file_path) if Path(file_path).is_absolute() else Path(workspace_path) / file_path
    if not path.exists():
        return {"status": "error", "error": f"File not found: {path}"}
    return {"status": "success", "content": path.read_text(encoding="utf-8"), "file_path": str(path)}


async def handle_write_file(file_path: str, content: str, workspace_path: str = ".", **_) -> dict:
    """Write content to a local file."""
    path = Path(file_path) if Path(file_path).is_absolute() else Path(workspace_path) / file_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"status": "success", "message": f"File written: {path}"}


async def handle_list_files(directory: str = ".", workspace_path: str = ".", **_) -> dict:
    """List files in a directory."""
    path = Path(directory) if Path(directory).is_absolute() else Path(workspace_path) / directory
    if not path.exists():
        return {"status": "error", "error": f"Directory not found: {path}"}
    files = [str(f.relative_to(path)) for f in sorted(path.rglob("*")) if f.is_file()]
    return {"status": "success", "files": files}


async def handle_ask_user(question: str, **_) -> dict:
    """Signals the workflow to pause and ask the user a question."""
    return {"status": "ask_user", "question": question}


async def handle_git_commit_push(
    commit_message: str = "Apply refactor changes",
    branch: str = "",
    remote: str = "origin",
    auto_stage_all: bool = True,
    workspace_path: str = ".",
    **_,
) -> dict:
    workspace = Path(workspace_path)

    def _run(cmd: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            cmd,
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

    git_check = _run(["git", "rev-parse", "--is-inside-work-tree"])
    if git_check.returncode != 0:
        return {
            "status": "error",
            "error": "Workspace is not a git repository.",
            "stderr": (git_check.stderr or "").strip()[-1000:],
        }

    if auto_stage_all:
        add_result = _run(["git", "add", "-A"])
        if add_result.returncode != 0:
            return {
                "status": "error",
                "error": "Failed to stage changes with git add -A.",
                "stderr": (add_result.stderr or "").strip()[-1000:],
            }

    status_result = _run(["git", "status", "--porcelain"])
    if status_result.returncode != 0:
        return {
            "status": "error",
            "error": "Failed to read git status.",
            "stderr": (status_result.stderr or "").strip()[-1000:],
        }

    if not (status_result.stdout or "").strip():
        return {
            "status": "success",
            "message": "No changes to commit.",
            "committed": False,
            "pushed": False,
        }

    commit_result = _run(["git", "commit", "-m", commit_message])
    if commit_result.returncode != 0:
        stderr_text = (commit_result.stderr or "").strip()
        if "nothing to commit" in stderr_text.lower():
            return {
                "status": "success",
                "message": "No new commit created because there were no staged changes.",
                "committed": False,
                "pushed": False,
            }
        return {
            "status": "error",
            "error": "Failed to create git commit.",
            "stderr": stderr_text[-1200:],
            "stdout": (commit_result.stdout or "").strip()[-1200:],
        }

    current_branch_result = _run(["git", "branch", "--show-current"])
    current_branch = (current_branch_result.stdout or "").strip()
    target_branch = branch.strip() or current_branch

    if not target_branch:
        return {
            "status": "error",
            "error": "Could not determine target branch for push. Provide branch explicitly.",
            "commit_output": (commit_result.stdout or "").strip()[-1200:],
        }

    push_result = _run(["git", "push", remote, target_branch])
    if push_result.returncode != 0:
        return {
            "status": "error",
            "error": "Commit created, but git push failed.",
            "committed": True,
            "pushed": False,
            "branch": target_branch,
            "remote": remote,
            "commit_output": (commit_result.stdout or "").strip()[-1200:],
            "stderr": (push_result.stderr or "").strip()[-1200:],
            "stdout": (push_result.stdout or "").strip()[-1200:],
        }

    return {
        "status": "success",
        "message": f"Changes committed and pushed to {remote}/{target_branch}.",
        "committed": True,
        "pushed": True,
        "branch": target_branch,
        "remote": remote,
        "commit_output": (commit_result.stdout or "").strip()[-1200:],
        "push_output": (push_result.stdout or "").strip()[-1200:],
    }


async def handle_github_put_file(
    local_file_path: str,
    repo_file_path: str = "",
    repo_name: str = "",
    branch: str = "",
    commit_message: str = "Update file via agent",
    workspace_path: str = ".",
    **_,
) -> dict:
    """Push a single file to GitHub via the Contents API (simple-agent style)."""

    def _git(cmd: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            cmd,
            cwd=str(workspace_path),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    token = (
        os.getenv("YOUR_GITHUB_ACCESS_TOKEN")
        or os.getenv("GITHUB_TOKEN")
        or os.getenv("GH_TOKEN")
        or ""
    ).strip()
    if not token:
        return {
            "status": "error",
            "error": "Missing GitHub token. Set YOUR_GITHUB_ACCESS_TOKEN (or GITHUB_TOKEN/GH_TOKEN) in the environment.",
        }

    detected_repo_name = ""
    if not repo_name.strip():
        remote = _git(["git", "remote", "get-url", "origin"])
        if remote.returncode == 0:
            url = (remote.stdout or "").strip()
            m = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^\s/]+?)(?:\.git)?$", url)
            if m:
                detected_repo_name = f"{m.group('owner')}/{m.group('repo')}"
        repo_name = detected_repo_name

    if not repo_name.strip() or "/" not in repo_name:
        return {
            "status": "error",
            "error": "repo_name is required (format: owner/repo) when it cannot be detected from git remote origin.",
        }

    if not branch.strip():
        b = _git(["git", "branch", "--show-current"])
        branch = (b.stdout or "").strip() or "main"

    workspace = Path(workspace_path)
    local_path = Path(local_file_path)
    resolved_local = local_path if local_path.is_absolute() else workspace / local_path
    if not resolved_local.exists():
        return {"status": "error", "error": f"Local file not found: {resolved_local}"}

    if not repo_file_path.strip():
        try:
            rel = resolved_local.relative_to(workspace)
            repo_file_path = rel.as_posix()
        except Exception:
            return {
                "status": "error",
                "error": "repo_file_path is required when local_file_path is outside workspace_path.",
            }
    repo_file_path = repo_file_path.lstrip("/")
    if repo_file_path.startswith(".."):
        return {"status": "error", "error": "repo_file_path must not traverse outside the repo."}

    content_b64 = base64.b64encode(resolved_local.read_bytes()).decode("utf-8")
    owner, repo = repo_name.split("/", 1)
    api_path = f"https://api.github.com/repos/{owner}/{repo}/contents/{urllib.parse.quote(repo_file_path)}"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "refactor-agent",
    }

    sha: str | None = None
    try:
        get_req = urllib.request.Request(
            api_path + "?ref=" + urllib.parse.quote(branch),
            headers=headers,
            method="GET",
        )
        with urllib.request.urlopen(get_req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            sha = data.get("sha")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            body = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else ""
            return {"status": "error", "error": f"GitHub GET failed: HTTP {e.code}", "details": body[-1200:]}
    except Exception as e:
        return {"status": "error", "error": f"GitHub GET failed: {type(e).__name__}: {str(e)[:200]}"}

    put_body = {
        "message": commit_message,
        "content": content_b64,
        "branch": branch,
    }
    if sha:
        put_body["sha"] = sha

    try:
        put_req = urllib.request.Request(
            api_path,
            data=json.dumps(put_body).encode("utf-8"),
            headers={**headers, "Content-Type": "application/json"},
            method="PUT",
        )
        with urllib.request.urlopen(put_req, timeout=30) as resp:
            out = json.loads(resp.read().decode("utf-8"))
            file_url = f"https://github.com/{owner}/{repo}/blob/{branch}/{repo_file_path}"
            commit_sha = ((out.get("commit") or {}).get("sha")) if isinstance(out, dict) else None
            return {
                "status": "success",
                "message": f"Pushed {repo_file_path} to {repo_name}@{branch} via GitHub API.",
                "repo": repo_name,
                "branch": branch,
                "repo_file_path": repo_file_path,
                "file_url": file_url,
                "commit_sha": commit_sha or "",
                "used_api": True,
            }
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else ""
        return {"status": "error", "error": f"GitHub PUT failed: HTTP {e.code}", "details": body[-1200:]}
    except Exception as e:
        return {"status": "error", "error": f"GitHub PUT failed: {type(e).__name__}: {str(e)[:200]}"}


# ──────────────────────────────────────────────
# TOOL DISPATCH TABLE
# Keys must match the 'name:' field in each config/tools/*.yaml file
# ──────────────────────────────────────────────

TOOL_HANDLERS = {
    "analyze_code": handle_analyze_code,
    "suggest_refactor": handle_suggest_refactor,
    "apply_refactor": handle_apply_refactor,
    "diff_preview": handle_diff_preview,
    "run_tests": handle_run_tests,
    "read_file": handle_read_file,
    "write_file": handle_write_file,
    "list_files": handle_list_files,
    "ask_user": handle_ask_user,
    "git_commit_push": handle_git_commit_push,
    "github_put_file": handle_github_put_file,
}
