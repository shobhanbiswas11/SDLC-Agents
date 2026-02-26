# repo_summarizer/cache_manager.py
"""
Metadata cache for diff-aware processing.

Stores previously extracted metadata per file so that on subsequent
webhook triggers we only re-extract metadata for files the payload
reports as changed. Everything else is loaded from cache.

Cache file: generated/{owner_repo}_cache.json
"""

import json
import os
import datetime
from typing import Dict, Set, Any, Optional


def _cache_path(repo_name: str) -> str:
    """Return the filesystem path for a repo's cache file."""
    return f"generated/{repo_name.replace('/', '_')}_cache.json"


def load_cache(repo_name: str) -> Dict[str, Any]:
    """
    Load the previous cache from disk.

    Returns a dict with:
      - file_metadata: {path: metadata_dict}
      - import_graph: {path: [imported_paths]}
      - last_updated: ISO timestamp
    """
    path = _cache_path(repo_name)
    if not os.path.exists(path):
        return {
            "file_metadata": {},
            "import_graph": {},
            "last_updated": None,
        }
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("file_metadata", {})
        data.setdefault("import_graph", {})
        data.setdefault("last_updated", None)
        return data
    except Exception:
        return {
            "file_metadata": {},
            "import_graph": {},
            "last_updated": None,
        }


def save_cache(
    repo_name: str,
    file_metadata: Dict[str, Any],
    import_graph: Dict[str, list],
) -> str:
    """Save cache to disk. Returns the path."""
    os.makedirs("generated", exist_ok=True)
    path = _cache_path(repo_name)
    data = {
        "file_metadata": file_metadata,
        "import_graph": import_graph,
        "last_updated": datetime.datetime.now().isoformat(),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path


def merge_metadata(
    cached_metadata: Dict[str, Any],
    fresh_metadata: Dict[str, Any],
    current_file_tree: Set[str],
) -> Dict[str, Any]:
    """
    Merge fresh metadata (for changed files) with cached metadata.
    Also removes entries for files that no longer exist in the repo.

    Args:
        cached_metadata:   Previous {path: metadata} from cache.
        fresh_metadata:    Newly extracted {path: metadata} for changed files.
        current_file_tree: Set of all current file paths (to prune deleted files).

    Returns:
        Merged {path: metadata} dict.
    """
    merged = {}

    # Keep cached entries that still exist and weren't re-extracted
    for path, meta in cached_metadata.items():
        if path in current_file_tree and path not in fresh_metadata:
            merged[path] = meta

    # Add/overwrite with fresh extractions
    merged.update(fresh_metadata)

    return merged
