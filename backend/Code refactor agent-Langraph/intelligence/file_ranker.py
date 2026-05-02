# repo_summarizer/file_ranker.py
import pathlib
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Set

SKIP_DIRS = {
    "tests", "test", "__pycache__", "node_modules", "dist", "build",
    ".git", ".github", ".vscode", ".idea",
    "coverage", ".coverage",
    "venv", ".venv", "env",
    "logs", "tmp", "temp",
    "cache", ".cache",
    "out", "target", "bin", "obj",
    "public/build", ".next", ".nuxt",
    "migrations/versions"
}

IMPORTANT_DIRS = {
    "src", "app", "api", "routes", "services", "controllers", "models",
    "lib", "server", "core", "config",
    "utils", "helpers", "middleware",
    "components", "hooks", "store",
    "views", "pages", "templates",
    "static", "public", "assets",
    "schemas", "validators",
    "repositories", "db", "database",
    "workers", "jobs", "tasks",
    "graphql", "resolvers",
    "plugins", "extensions"
}

ENTRY_STEMS = {
    "main", "app", "server", "index", "cli", "manage", "run",
    "start", "boot", "init", "entry",
    "wsgi", "asgi",
    "application",
    "dev", "prod",
    "worker",
    "script"
}

def _depth_penalty(path: str) -> int:
    return len(path.split("/")) - 1

def _folder_boost(parts: List[str]) -> int:
    for p in parts:
        if p in IMPORTANT_DIRS:
            return -20
    return 0

def _filename_boost(stem: str) -> int:
    if stem in ENTRY_STEMS or stem.startswith("app") or stem.startswith("server"):
        return -40
    if stem in ("routes", "router", "routes"):
        return -25
    if stem in ("config", "settings"):
        return -20
    return 0

def compute_in_degree(graph: Dict[str, Set[str]]) -> Dict[str, int]:
    indeg = Counter()
    for src, deps in graph.items():
        for d in deps:
            indeg[d] += 1
    return dict(indeg)

def rank_files(file_map: Dict[str, str],
               file_tree: List[str],
               graph: Dict[str, Set[str]],
               top_k: int = 12,
               include_all: bool = False) -> List[Tuple[str, float]]:
    """
    Returns list of (path, score) sorted ascending (lower score == more important)
    If include_all=True, returns all files but still ordered by score.
    """
    indeg = compute_in_degree(graph)
    scores = {}
    for path in file_tree:
        parts = path.lower().split("/")
        # skip binary-ish or extremely large file types from consideration
        ext = pathlib.Path(path).suffix.lower()
        if any(p in SKIP_DIRS for p in parts):
            # give them a high (worse) score if they are skip dirs
            scores[path] = 9999
            continue
        stem = pathlib.Path(path).stem.lower()
        score = 100.0
        # filename and folder heuristics
        score += _depth_penalty(path)
        score += _folder_boost(parts)
        score += _filename_boost(stem)
        # presence in import graph (lower = more central)
        graph_score = - (indeg.get(path, 0) * 10)
        score += graph_score
        # md files are important for docs but not for code understanding;
        # allow them but keep moderate priority
        if ext == ".md":
            score -= 30
        # small preference for source files we have content for
        if path not in file_map or not file_map.get(path):
            score += 200
        scores[path] = score

    ordered = sorted(scores.items(), key=lambda kv: kv[1])
    if include_all:
        return ordered
    else:
        return ordered[:top_k]