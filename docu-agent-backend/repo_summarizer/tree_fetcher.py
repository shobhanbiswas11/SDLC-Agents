# repo_summarizer/tree_fetcher.py
import requests
import os
from typing import Tuple, Dict, List, Callable, Optional

# If you already have a `load_github_repo` utility that returns (documents, file_tree),
# you can pass it to fetch_full_repo to reuse it; otherwise we'll use the GitHub REST API.

def fetch_tree_via_github_api(owner: str, repo: str, token: str, branch: str = "main") -> List[str]:
    """Return list of file paths in repo (recursive)."""
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    headers = {"Authorization": f"token {token}"} if token else {}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    tree = resp.json().get("tree", [])
    return [entry["path"] for entry in tree if entry["type"] == "blob"]

def fetch_file_content_github(owner: str, repo: str, path: str, token: str, branch: str = "main") -> str:
    """Fetch raw file content using GitHub contents API (best-effort)."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3.raw"} if token else {"Accept": "application/vnd.github.v3.raw"}
    resp = requests.get(url, headers=headers, params={"ref": branch}, timeout=30)
    resp.raise_for_status()
    return resp.text

def fetch_full_repo(repo: str,
                    token: str,
                    branch: str = "main",
                    loader_fn: Optional[Callable] = None,
                    prefer_loader: bool = True) -> Tuple[Dict[str, str], List[str]]:
    """
    Returns (file_map, file_tree).
    - file_map: {path: content}
    - file_tree: list of paths
    If loader_fn is provided and prefer_loader is True, it will be used (expected to return documents, file_tree).
    Otherwise fallback to GitHub API.
    """
    owner, name = repo.split("/", 1)
    if loader_fn and prefer_loader:
        try:
            documents, file_tree = loader_fn(repo=repo, access_token=token, branch=branch)
            file_map = {}
            for doc in documents:
                src = doc.metadata.get("source") or doc.metadata.get("path") or "unknown"
                file_map[src] = doc.page_content
            return file_map, file_tree
        except Exception:
            # fallback to API below
            pass

    # Use GitHub API fallback
    paths = fetch_tree_via_github_api(owner, name, token, branch)
    file_map = {}
    for p in paths:
        try:
            file_map[p] = fetch_file_content_github(owner, name, p, token, branch)
        except Exception:
            # best-effort: skip unreadable files (binary, LFS, etc.)
            file_map[p] = ""
    return file_map, paths