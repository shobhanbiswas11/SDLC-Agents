# app/services/repo_service.py
import re
import shutil
import subprocess
import tempfile
from typing import Optional


def sanitize_github_url(url: str) -> tuple[str, Optional[str]]:
    """
    Clean a GitHub URL so it works with `git clone`.
    Also extracts the branch if the URL contains /tree/<branch> or /blob/<branch>.

    Returns:
        (clean_url, branch_or_None)

    e.g.  https://github.com/user/repo/tree/feature/login
        → ("https://github.com/user/repo.git", "feature/login")
    """
    url = url.strip().rstrip("/")

    # Try to extract branch from /tree/<branch> or /blob/<branch>/...
    branch = None
    match = re.search(r"/(tree|blob)/(.+?)(?:/.*)?$", url)
    if match:
        branch = match.group(2)

    # Remove /tree/... or /blob/... suffixes
    url = re.sub(r"/(tree|blob)/[^/]+(/.*)?$", "", url)
    # Ensure it ends with .git (optional, but safe)
    if not url.endswith(".git"):
        url += ".git"
    return url, branch


def clone_repository(repo_url: str, branch: Optional[str] = None) -> str:
    """
    Clone a repository to a temp directory.
    If `branch` is provided, clone only that branch.
    Otherwise, extracts the branch from the URL (if present), or clones the default branch.
    """
    clean_url, url_branch = sanitize_github_url(repo_url)
    # Use explicit branch param first, then fall back to URL-extracted branch
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


def list_remote_branches(repo_url: str) -> list[dict]:
    """
    List all branches of a remote repository using `git ls-remote --heads`.
    Returns a list of dicts: [{"name": "main", "sha": "abc123..."}, ...]
    """
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
        raise RuntimeError(f"Failed to list branches: {result.stderr.strip()}")

    branches = []
    for line in result.stdout.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) == 2:
            sha = parts[0].strip()
            ref = parts[1].strip()
            # refs/heads/main → main
            name = ref.replace("refs/heads/", "")
            branches.append({"name": name, "sha": sha[:12]})

    # Sort: common default branches first, then alphabetical
    priority = {"main": 0, "master": 1, "develop": 2, "dev": 3}
    branches.sort(key=lambda b: (priority.get(b["name"], 100), b["name"]))

    return branches
