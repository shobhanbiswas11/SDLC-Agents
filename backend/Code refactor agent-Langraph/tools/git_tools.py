"""
tools/git_tools.py — Git and GitHub integration tool handlers.

Handlers:
  handle_git_commit_push — stage, commit, and push changes via git CLI
  handle_github_put_file — push a single file via the GitHub Contents REST API
"""

from __future__ import annotations

import asyncio
import base64
import json as _json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from tools._shared import normalize_github_repo_url, resolve_file_in_workspace
from core.logging import get_logger

logger = get_logger(__name__)


async def handle_git_commit_push(
    commit_message: str = "Apply refactor changes",
    branch: str = "",
    remote: str = "origin",
    auto_stage_all: bool = True,
    workspace_path: str = ".",
    **_,
) -> dict:
    """Stage, commit, and push changes in the workspace git repository."""
    workspace = Path(workspace_path)

    # Prefer an adhoc-cloned repo when the agent ran from its own directory
    adhoc_clone_root = Path(__file__).resolve().parent.parent / ".refactor_repos" / "adhoc"
    if adhoc_clone_root.exists():
        clones = sorted(adhoc_clone_root.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        for candidate in clones:
            if (candidate / ".git").exists():
                workspace = candidate
                break

    async def _run(cmd: list[str]) -> subprocess.CompletedProcess:
        return await asyncio.to_thread(
            subprocess.run,
            cmd,
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

    # Validate this is a git repo
    git_check = await _run(["git", "rev-parse", "--is-inside-work-tree"])
    if git_check.returncode != 0:
        return {
            "status": "error",
            "error": "Workspace is not a git repository.",
            "stderr": (git_check.stderr or "").strip()[-1000:],
        }

    if auto_stage_all:
        add_result = await _run(["git", "add", "-A"])
        if add_result.returncode != 0:
            return {
                "status": "error",
                "error": "Failed to stage changes with git add -A.",
                "stderr": (add_result.stderr or "").strip()[-1000:],
            }

    status_result = await _run(["git", "status", "--porcelain"])
    if status_result.returncode != 0:
        return {
            "status": "error",
            "error": "Failed to read git status.",
            "stderr": (status_result.stderr or "").strip()[-1000:],
        }

    if not (status_result.stdout or "").strip():
        return {"status": "success", "message": "No changes to commit.", "committed": False, "pushed": False}

    commit_result = await _run(["git", "commit", "-m", commit_message])
    if commit_result.returncode != 0:
        stderr_text = (commit_result.stderr or "").strip()
        if "nothing to commit" in stderr_text.lower():
            return {
                "status": "success",
                "message": "No new commit created — no staged changes.",
                "committed": False,
                "pushed": False,
            }
        return {
            "status": "error",
            "error": "Failed to create git commit.",
            "stderr": stderr_text[-1200:],
            "stdout": (commit_result.stdout or "").strip()[-1200:],
        }

    current_branch_result = await _run(["git", "branch", "--show-current"])
    current_branch = (current_branch_result.stdout or "").strip()
    target_branch = branch.strip() or current_branch

    if not target_branch:
        return {
            "status": "error",
            "error": "Could not determine target branch for push. Provide branch explicitly.",
            "commit_output": (commit_result.stdout or "").strip()[-1200:],
        }

    push_result = await _run(["git", "push", remote, target_branch])
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

    logger.info("git_commit_push: pushed to %s/%s", remote, target_branch)
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
    repo_url: str,
    file_path: str,
    commit_message: str,
    content: str = "staged",
    branch: str = "",
    workspace_path: str = ".",
    **_,
) -> dict:
    """
    Push a single file to GitHub via the Contents API (no local git required).

    Reads ``YOUR_GITHUB_ACCESS_TOKEN`` from the environment.
    If ``content='staged'``, reads the staged refactoring file produced by
    ``suggest_refactor``.
    """
    token = os.getenv("YOUR_GITHUB_ACCESS_TOKEN", "").strip()
    if not token:
        return {"status": "error", "error": "YOUR_GITHUB_ACCESS_TOKEN is not set in .env"}

    resolved_file = resolve_file_in_workspace(file_path, workspace_path)
    repo_file_path = file_path.lstrip("/")
    if resolved_file is not None:
        try:
            repo_file_path = str(resolved_file.relative_to(Path(workspace_path).resolve())).replace("\\", "/")
        except ValueError:
            repo_file_path = file_path.lstrip("/")

    # Resolve staged content if requested
    staging_file: Path | None = None
    content_source = "provided"
    if content == "staged" or not (content or "").strip():
        stem = Path(repo_file_path).stem
        suffix = Path(repo_file_path).suffix
        staging_file = Path(workspace_path) / ".refactor_staging" / f"{stem}_staged{suffix}"
        if staging_file.exists():
            content = staging_file.read_text(encoding="utf-8")
            content_source = "staged"
        elif resolved_file is not None and resolved_file.exists():
            # apply_refactor consumes/deletes the staged file after writing to disk.
            # In that normal flow, push the already-applied local file content.
            content = resolved_file.read_text(encoding="utf-8")
            content_source = "applied_file"
        else:
            return {
                "status": "error",
                "error": (
                    "No staged refactoring found and the target file could not be resolved "
                    "from the workspace. Call suggest_refactor/apply_refactor first, or pass "
                    "explicit content to github_put_file."
                ),
            }

    # Parse owner/repo from the URL
    norm = normalize_github_repo_url(repo_url)
    if not norm:
        return {"status": "error", "error": f"Invalid GitHub repo URL: {repo_url}"}
    parts = [p for p in urllib.parse.urlparse(norm).path.split("/") if p]
    if len(parts) < 2:
        return {"status": "error", "error": f"Cannot parse owner/repo from: {norm}"}
    owner, repo = parts[0], parts[1]

    encoded_content = base64.b64encode(content.encode("utf-8")).decode("ascii")
    api_path = repo_file_path
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{api_path}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }

    # Get the current file SHA (required for updates, not for new files)
    sha: str | None = None
    get_url = api_url + (f"?ref={branch}" if branch else "")
    get_req = urllib.request.Request(get_url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(get_req, timeout=15) as resp:
            sha = _json.loads(resp.read().decode("utf-8")).get("sha")
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            return {"status": "error", "error": f"GitHub API error checking file: HTTP {exc.code}"}
    except Exception as exc:
        return {"status": "error", "error": f"Network error checking file: {str(exc)}"}

    payload: dict = {"message": commit_message, "content": encoded_content}
    if sha:
        payload["sha"] = sha
    if branch:
        payload["branch"] = branch

    put_req = urllib.request.Request(
        api_url,
        data=_json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="PUT",
    )
    try:
        with urllib.request.urlopen(put_req, timeout=30) as resp:
            result_data = _json.loads(resp.read().decode("utf-8"))
        if staging_file is not None and content_source == "staged":
            staging_file.unlink(missing_ok=True)
        commit_info = result_data.get("commit", {})
        logger.info("github_put_file: pushed %s/%s/%s", owner, repo, api_path)
        return {
            "status": "success",
            "message": f"✅ File pushed to GitHub: {owner}/{repo}/{api_path}",
            "commit_sha": commit_info.get("sha", ""),
            "commit_url": commit_info.get("html_url", ""),
            "file_url": result_data.get("content", {}).get("html_url", ""),
            "content_source": content_source,
        }
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        return {"status": "error", "error": f"GitHub API push failed: HTTP {exc.code}: {body[:300]}"}
    except Exception as exc:
        return {"status": "error", "error": f"Failed to push file: {str(exc)}"}
