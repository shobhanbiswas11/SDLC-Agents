"""Thin wrappers around the `git` binary for cloning and listing branches."""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from typing import List, Optional, Tuple


def sanitize_github_url(url: str) -> Tuple[str, Optional[str]]:
    """Strip /tree/<branch> or /blob/<branch> from a GitHub URL.

    Returns (clean_url, branch_or_None).
    """
    url = url.strip().rstrip("/")

    branch: Optional[str] = None
    match = re.search(r"/(tree|blob)/(.+?)(?:/.*)?$", url)
    if match:
        branch = match.group(2)

    url = re.sub(r"/(tree|blob)/[^/]+(/.*)?$", "", url)
    if not url.endswith(".git"):
        url += ".git"
    return url, branch


def clone_repository(repo_url: str, branch: Optional[str] = None) -> str:
    """Shallow-clone the repo into a temp dir and return its path."""
    clean_url, url_branch = sanitize_github_url(repo_url)
    target_branch = branch or url_branch

    git_executable = shutil.which("git")
    if not git_executable:
        raise RuntimeError(
            "Git is not available in the backend runtime. "
            "Install the `git` binary in the backend container."
        )

    temp_dir = tempfile.mkdtemp()
    cmd = [git_executable, "clone", "--depth", "1"]
    if target_branch:
        cmd += ["--branch", target_branch]
    cmd += [clean_url, temp_dir]

    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return temp_dir


def list_remote_branches(repo_url: str) -> List[dict]:
    """Use `git ls-remote --heads` to enumerate remote branches."""
    clean_url, _ = sanitize_github_url(repo_url)
    git_executable = shutil.which("git")
    if not git_executable:
        raise RuntimeError(
            "Git is not available in the backend runtime. "
            "Install the `git` binary in the backend container."
        )

    result = subprocess.run(
        [git_executable, "ls-remote", "--heads", clean_url],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to list branches: {result.stderr.strip()}"
        )

    branches: List[dict] = []
    for line in result.stdout.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) == 2:
            sha = parts[0].strip()
            ref = parts[1].strip()
            name = ref.replace("refs/heads/", "")
            branches.append({"name": name, "sha": sha[:12]})

    priority = {"main": 0, "master": 1, "develop": 2, "dev": 3}
    branches.sort(key=lambda b: (priority.get(b["name"], 100), b["name"]))
    return branches
