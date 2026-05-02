"""
tools/_shared.py — Internal helpers shared across all tool modules.

These utilities handle URL normalisation, GitHub path resolution,
workspace file lookup, and the internal LLM client used by tool handlers.
They are intentionally private (prefixed with _) and not part of the public API.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import time as _time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from core.logging import get_logger

logger = get_logger(__name__)

# ── LLM client (tools-internal, separate TTL from agent client) ────────────────

_tools_cached_client = None
_tools_cached_client_time = 0.0
_TOOLS_CLIENT_TTL = 1800  # 30 minutes


def _get_tools_llm_client():
    """Cached AsyncAzureOpenAI client for tool-internal LLM calls."""
    global _tools_cached_client, _tools_cached_client_time
    if _tools_cached_client and (_time.time() - _tools_cached_client_time) < _TOOLS_CLIENT_TTL:
        return _tools_cached_client

    from openai import AsyncAzureOpenAI
    from azure.identity import ClientSecretCredential

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
    tenant_id = os.getenv("AZURE_TENANT_ID", "")
    client_id = os.getenv("AZURE_CLIENT_ID", "")
    client_secret = os.getenv("AZURE_CLIENT_SECRET", "")

    if tenant_id and client_id and client_secret:
        cred = ClientSecretCredential(tenant_id, client_id, client_secret)
        token_obj = cred.get_token("https://cognitiveservices.azure.com/.default")
        client = AsyncAzureOpenAI(
            azure_endpoint=endpoint, api_version=api_version, api_key=token_obj.token
        )
    else:
        client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_version=api_version,
            api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
        )

    _tools_cached_client = client
    _tools_cached_client_time = _time.time()
    return client


async def call_llm(system_msg: str, user_msg: str, max_tokens: int = 4096) -> str:
    """Call Azure OpenAI for refactoring analysis. Returns the LLM response text."""
    client = _get_tools_llm_client()
    deployment = (
        os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT")
        or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    )
    try:
        response = await client.chat.completions.create(
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
    except Exception as exc:
        logger.error("call_llm failed: %s", exc)
        return f"[LLM Error: {str(exc)}]"


# ── URL helpers ────────────────────────────────────────────────────────────────

def _extract_first_http_url(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    match = re.search(r"https?://\S+", text)
    if not match:
        return ""
    return match.group(0).strip("'\"),.;>]")


def _normalize_url_candidate(value: str) -> str:
    """Normalise pasted URL-like inputs that may include trailing punctuation or extra text."""
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
    if first_token.startswith(("github.com/", "www.github.com/")):
        first_token = f"https://{first_token}"
    return first_token.strip("'\"),.;>]")


def is_http_url(value: str) -> bool:
    parsed = urllib.parse.urlparse(_normalize_url_candidate(value))
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def github_blob_to_raw(url: str) -> str:
    """Convert a GitHub blob URL to the raw content URL; return input unchanged if not a blob URL."""
    normalized = _normalize_url_candidate(url)
    parsed = urllib.parse.urlparse(normalized)
    if parsed.netloc not in {"github.com", "www.github.com"}:
        return url
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 5 and parts[2] == "blob":
        owner, repo, _, branch = parts[:4]
        file_path = "/".join(parts[4:])
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"
    return url


def _github_blob_repo_and_path(url: str) -> tuple[str, str] | None:
    """Return (repo_url, repo_relative_path) for a GitHub blob URL, else None."""
    normalized = _normalize_url_candidate(url)
    parsed = urllib.parse.urlparse(normalized)
    if parsed.netloc not in {"github.com", "www.github.com"}:
        return None
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 5 and parts[2] == "blob":
        owner, repo, _, _branch = parts[:4]
        file_path = "/".join(parts[4:])
        return (f"https://github.com/{owner}/{repo}", file_path)
    return None


def _github_blob_parts(url: str) -> tuple[str, str, str] | None:
    """Return (repo_url, branch, repo_relative_path) for a GitHub blob URL."""
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


def normalize_github_repo_url(repo_url: str) -> str:
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
    repo = parts[1].removesuffix(".git")
    return f"https://github.com/{owner}/{repo}"


def _workspace_github_repo_url(workspace_path: str) -> str:
    """Best-effort read of the git remote.origin.url as a normalised GitHub URL."""
    workspace = Path(workspace_path)
    if not workspace.exists():
        return ""
    try:
        result = subprocess.run(
            ["git", "-C", str(workspace), "config", "--get", "remote.origin.url"],
            capture_output=True, text=True, timeout=5, check=False,
        )
        return normalize_github_repo_url(result.stdout.strip()) if result.returncode == 0 else ""
    except Exception:
        return ""


def github_session_repo_mismatch_error(file_path: str, workspace_path: str) -> str | None:
    """
    In GitHub-backed sessions, return an error string when a blob URL points
    to a different repo than the currently cloned workspace.
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
    # If the file already exists in this workspace, it's fine
    try:
        candidate = Path(workspace_path) / requested_rel_path
        if candidate.exists() and candidate.is_file():
            return None
    except Exception:
        pass
    if normalize_github_repo_url(requested_repo) == normalize_github_repo_url(current_repo):
        return None
    return (
        "GitHub session repository mismatch detected. "
        f"Current session repo: {current_repo}. "
        f"Requested file repo: {requested_repo} (path: {requested_rel_path}). "
        "Start a NEW workflow with source_type='github' and github_url set to the "
        "requested repo, then use repository-relative file paths in that new session."
    )


def _is_safe_repo_relative_path(repo_path: str) -> bool:
    text = (repo_path or "").strip().replace("\\", "/")
    if not text or text.startswith("/"):
        return False
    parts = [part for part in text.split("/") if part not in {"", "."}]
    return all(part != ".." for part in parts)


def _clone_repo_if_needed(
    repo_url: str, branch: str, clone_path: Path
) -> tuple[bool, str | None]:
    """Ensure a repo is cloned at clone_path. Returns (ok, error_message)."""
    try:
        if (clone_path / ".git").exists():
            origin = _workspace_github_repo_url(str(clone_path))
            if normalize_github_repo_url(origin) == normalize_github_repo_url(repo_url):
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
    except Exception as exc:
        return False, f"Failed to auto-clone repository: {str(exc)}"


def resolve_blob_url_to_local_file(
    file_path: str, workspace_path: str
) -> tuple[Path | None, str | None, str | None]:
    """
    Resolve a GitHub blob URL to a local filesystem path.

    Returns:
        (resolved_path, error_message, informational_note)
    """
    parts = _github_blob_parts(file_path)
    if not parts:
        return None, "Only GitHub blob URLs are supported for this operation.", None

    repo_url, branch, repo_rel_path = parts
    if not _is_safe_repo_relative_path(repo_rel_path):
        return None, "Unsafe repository file path detected in URL.", None

    is_github_backed = ".refactor_repos" in (workspace_path or "")
    if is_github_backed:
        mismatch_error = github_session_repo_mismatch_error(file_path, workspace_path)
        if mismatch_error:
            return None, mismatch_error, None
        resolved = Path(workspace_path) / repo_rel_path
        if not resolved.exists():
            return None, f"File not found in current GitHub-backed workspace: {resolved}", None
        return resolved, None, "Mapped GitHub blob URL to current session workspace file."

    repo_key = hashlib.sha1(
        f"{normalize_github_repo_url(repo_url)}@{branch}".encode("utf-8")
    ).hexdigest()[:12]
    clone_root = Path(__file__).resolve().parent.parent / ".refactor_repos" / "adhoc"
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


def fetch_text_from_url(url: str, timeout: int = 20) -> tuple[str | None, str | None]:
    """Fetch UTF-8 text from URL. Returns (content, error)."""
    req = urllib.request.Request(url, headers={"User-Agent": "refactor-agent"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8"), None
    except urllib.error.HTTPError as exc:
        return None, f"HTTP {exc.code} while fetching URL: {url}"
    except urllib.error.URLError as exc:
        return None, f"Network error while fetching URL: {exc.reason}"
    except UnicodeDecodeError:
        return None, "Remote file is not UTF-8 text."
    except Exception as exc:
        return None, f"Failed to fetch URL: {str(exc)}"


def resolve_file_in_workspace(file_path: str, workspace_path: str) -> Path | None:
    """
    Resolve a file path relative to the workspace.

    Falls back to a recursive search on the bare filename so nested files like
    ``src/pages/Login.tsx`` or just ``Login.tsx`` are always found.
    """
    workspace = Path(workspace_path)
    direct = Path(file_path) if Path(file_path).is_absolute() else workspace / file_path
    if direct.exists() and direct.is_file():
        return direct
    bare_name = Path(file_path).name
    for match in workspace.rglob(bare_name):
        if match.is_file():
            return match
    return None
