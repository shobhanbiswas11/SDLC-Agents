# repo_summarizer/tree_fetcher.py
import requests
import os
import time
import pathlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple, Dict, List, Callable, Optional

# ── Pre-download skip filter ──────────────────────────────────────────────────
# These paths/extensions are skipped BEFORE downloading to avoid wasted API calls.

_SKIP_PATH_SEGMENTS = {
    "node_modules", ".git", "dist", "build", ".next", "__pycache__",
    ".cache", "coverage", ".nyc_output", "vendor", "venv", ".venv",
    "env", ".env", "eggs", ".eggs", "generated", "memory"
}

_SKIP_EXTENSIONS = {
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".bmp", ".tiff",
    # Fonts
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    # Video / audio
    ".mp4", ".mp3", ".wav", ".ogg", ".avi", ".mov",
    # Archives
    ".zip", ".gz", ".tar", ".7z", ".rar",
    # Documents
    ".pdf", ".docx", ".xlsx", ".pptx",
    # Compiled / binary
    ".pyc", ".pyo", ".class", ".o", ".so", ".dll", ".exe",
    # Source maps and lock files (large and useless for README)
    ".map", ".lock",
}

_SKIP_FILENAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "Pipfile.lock", "poetry.lock", "uv.lock",
    ".DS_Store", "Thumbs.db",
}

_MAX_FILES = 200  # safety cap: never fetch more than this many files

# ── In-Memory Cache ───────────────────────────────────────────────────────────
# Cache to prevent redundantly fetching the same repo on repeated chat requests.
# Format: { "cache_key": (timestamp, (file_map, file_tree)) }
_REPO_CACHE: Dict[str, Tuple[float, Tuple[Dict[str, str], List[str]]]] = {}
_CACHE_TTL = 300  # 5 minutes expiration


def _should_skip_path(path: str) -> bool:
    """Return True if the file should be skipped entirely before downloading."""
    parts = path.lower().split("/")

    # Skip if any path segment is a known junk directory
    for segment in parts:
        if segment in _SKIP_PATH_SEGMENTS:
            return True

    name = pathlib.Path(path).name.lower()
    ext = pathlib.Path(path).suffix.lower()

    if name in _SKIP_FILENAMES:
        return True
    if ext in _SKIP_EXTENSIONS:
        return True

    return False


# ── GitHub API helpers ────────────────────────────────────────────────────────

def fetch_tree_via_github_api(owner: str, repo: str, token: str, branch: str = "main", max_retries: int = 3) -> List[str]:
    """Return list of file paths in repo (recursive). Built-in retry for intermittent SSL errors."""
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    headers = {"Authorization": f"token {token}"} if token else {}
    
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            tree = resp.json().get("tree", [])
            return [entry["path"] for entry in tree if entry["type"] == "blob"]
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise
            print(f"[fetch-tree] Network error (attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(2)
            
    return []


def _fetch_one(owner: str, repo: str, path: str, token: str, branch: str) -> Tuple[str, str]:
    """Fetch a single file. Returns (path, content). On error returns (path, '')."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3.raw",
    } if token else {"Accept": "application/vnd.github.v3.raw"}
    try:
        resp = requests.get(url, headers=headers, params={"ref": branch}, timeout=30)
        resp.raise_for_status()
        return path, resp.text
    except Exception:
        return path, ""


def fetch_full_repo(
    repo: str,
    token: str,
    branch: str = "main",
    loader_fn: Optional[Callable] = None,
    prefer_loader: bool = True,
    max_workers: int = 20,
) -> Tuple[Dict[str, str], List[str]]:
    """
    Returns (file_map, file_tree).
    - file_map: {path: content}  (only fetchable, non-skipped source files)
    - file_tree: list of ALL paths (including skipped ones, for structure display)

    Key improvements over old version:
    - Pre-filters binary/junk files BEFORE downloading (saves many API calls)
    - Fetches all remaining files in PARALLEL using ThreadPoolExecutor
    - Caps at _MAX_FILES to avoid runaway fetching on huge repos
    """
    owner, name = repo.split("/", 1)
    
    cache_key = f"github:{repo}:{branch}"
    now = time.time()
    
    if cache_key in _REPO_CACHE:
        cached_time, cached_result = _REPO_CACHE[cache_key]
        if now - cached_time < _CACHE_TTL:
            print(f"[fetch] Instant serving from in-memory cache: {cache_key}")
            return cached_result
        else:
            del _REPO_CACHE[cache_key]

    # Try custom loader first (if available)
    if loader_fn and prefer_loader:
        try:
            documents, file_tree = loader_fn(repo=repo, access_token=token, branch=branch)
            file_map = {}
            for doc in documents:
                src = doc.metadata.get("source") or doc.metadata.get("path") or "unknown"
                file_map[src] = doc.page_content
            return file_map, file_tree
        except Exception:
            pass  # fall through to GitHub API

    # ── Step 1: Fetch file tree (single API call) ─────────────────────────────
    t0 = time.perf_counter()
    all_paths = fetch_tree_via_github_api(owner, name, token, branch)
    t1 = time.perf_counter()
    print(f"[fetch] Repo tree: {len(all_paths)} total files found in {t1 - t0:.1f}s")

    # ── Step 2: Pre-filter before downloading ─────────────────────────────────
    to_fetch = [p for p in all_paths if not _should_skip_path(p)]

    # Apply safety cap (prioritise smaller files / shallower paths first)
    if len(to_fetch) > _MAX_FILES:
        to_fetch = sorted(to_fetch, key=lambda p: (len(p.split("/")), p))[:_MAX_FILES]
        print(f"[fetch] Capped at {_MAX_FILES} files (repo is very large)")

    skipped = len(all_paths) - len(to_fetch)
    print(f"[fetch] Fetching {len(to_fetch)} files in parallel (skipping {skipped} binary/lock/dist files)...")

    # ── Step 3: Parallel file download ────────────────────────────────────────
    t2 = time.perf_counter()
    file_map: Dict[str, str] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_fetch_one, owner, name, p, token, branch): p
            for p in to_fetch
        }
        for future in as_completed(futures):
            path, content = future.result()
            file_map[path] = content

    t3 = time.perf_counter()
    successful = sum(1 for v in file_map.values() if v)
    print(f"[fetch] Downloaded {successful}/{len(to_fetch)} files in {t3 - t2:.1f}s "
          f"(parallel, {max_workers} workers)")

    result = (file_map, all_paths)
    _REPO_CACHE[cache_key] = (time.time(), result)
    
    # Return all_paths as file_tree so the repo structure display is complete
    return result


def fetch_local_repo(local_path: str, max_files: int = _MAX_FILES) -> Tuple[Dict[str, str], List[str]]:
    """
    Scans a local directory instead of using the GitHub API.
    Returns (file_map, file_tree) just like fetch_full_repo.
    """
    root_path = pathlib.Path(local_path).resolve()
    
    if not root_path.exists() or not root_path.is_dir():
        raise ValueError(f"Local path does not exist or is not a directory: {local_path}")
        
    cache_key = f"local:{str(root_path)}"
    now = time.time()
    
    if cache_key in _REPO_CACHE:
        cached_time, cached_result = _REPO_CACHE[cache_key]
        if now - cached_time < _CACHE_TTL:
            print(f"[fetch-local] Instant serving from in-memory cache: {cache_key}")
            return cached_result
        else:
            del _REPO_CACHE[cache_key]
            
    all_paths = []
    
    # ── Step 1: Walk local directory ──────────────────────────────────────────
    for root, dirs, files in os.walk(str(root_path)):
        # Filter directories in-place to prevent os.walk from entering ignored folders
        dirs[:] = [d for d in dirs if not _should_skip_path(d)]
        
        for file in files:
            full_path = os.path.join(root, file)
            # Calculate relative path (e.g. "src/main.py")
            rel_path = os.path.relpath(full_path, str(root_path))
            
            # Use posix paths internally to match github structure ("/")
            rel_path_posix = rel_path.replace(os.sep, "/")
            all_paths.append(rel_path_posix)

    print(f"[fetch-local] Local tree: {len(all_paths)} total files found in {local_path}")
    
    # ── Step 2: Pre-filter before reading ─────────────────────────────────────
    to_fetch = [p for p in all_paths if not _should_skip_path(p)]
    
    # Cap files
    if len(to_fetch) > max_files:
        to_fetch = sorted(to_fetch, key=lambda p: (len(p.split("/")), p))[:max_files]
        print(f"[fetch-local] Capped at {max_files} files (repo is very large)")

    skipped = len(all_paths) - len(to_fetch)
    print(f"[fetch-local] Reading {len(to_fetch)} local files (skipping {skipped} binary/lock/dist files)...")

    # ── Step 3: Read files from disk ──────────────────────────────────────────
    file_map: Dict[str, str] = {}
    successful = 0
    
    for rel_path in to_fetch:
        full_path = root_path / rel_path
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
                file_map[rel_path] = content
                successful += 1
        except Exception:
            pass

    print(f"[fetch-local] Read {successful}/{len(to_fetch)} local files successfully")
    
    result = (file_map, all_paths)
    _REPO_CACHE[cache_key] = (time.time(), result)
    
    return result