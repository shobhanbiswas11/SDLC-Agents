# app/services/repo_service.py
import re
import subprocess
import tempfile


def sanitize_github_url(url: str) -> str:
    """
    Clean a GitHub URL so it works with `git clone`.
    Strips /tree/<branch>, /blob/<branch>/..., and trailing slashes.
    e.g. https://github.com/user/repo/tree/main → https://github.com/user/repo
    """
    url = url.strip().rstrip("/")
    # Remove /tree/... or /blob/... suffixes
    url = re.sub(r"/(tree|blob)/[^/]+(/.*)?$", "", url)
    # Ensure it ends with .git (optional, but safe)
    if not url.endswith(".git"):
        url += ".git"
    return url


def clone_repository(repo_url: str) -> str:
    clean_url = sanitize_github_url(repo_url)
    temp_dir = tempfile.mkdtemp()

    subprocess.run(["git", "clone", clean_url, temp_dir], check=True)

    return temp_dir
