"""
Repository service — clone a remote repo and detect the ecosystem(s) present.
"""

from __future__ import annotations

import shutil
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from git import Repo

from app.config import get_settings


class Ecosystem(str, Enum):
    PYTHON = "python"
    NODE = "node"


# Files that signal a given ecosystem
_ECOSYSTEM_MARKERS: dict[Ecosystem, list[str]] = {
    Ecosystem.PYTHON: [
        "requirements.txt",
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "Pipfile",
    ],
    Ecosystem.NODE: [
        "package.json",
    ],
}


@dataclass
class RepoInfo:
    """Represents a cloned (or local) repository."""

    path: Path
    ecosystems: list[Ecosystem] = field(default_factory=list)
    dependency_files: dict[Ecosystem, list[Path]] = field(default_factory=dict)


def _detect_ecosystems(repo_path: Path) -> dict[Ecosystem, list[Path]]:
    """Walk the repo root and return ecosystem → list of dependency files."""
    found: dict[Ecosystem, list[Path]] = {}
    for eco, markers in _ECOSYSTEM_MARKERS.items():
        files: list[Path] = []
        for marker in markers:
            # Search only top-level and one level deep (monorepo support)
            for p in repo_path.rglob(marker):
                # skip node_modules, .venv, etc.
                parts = p.relative_to(repo_path).parts
                if any(
                    part.startswith(".")
                    or part in ("node_modules", "__pycache__", ".venv", "venv")
                    for part in parts
                ):
                    continue
                files.append(p)
        if files:
            found[eco] = files
    return found


def load_repo(repo_url: str) -> RepoInfo:
    """
    Clone a remote repo (or use a local path) and return a RepoInfo
    with detected ecosystems and relevant dependency files.
    """
    settings = get_settings()
    repo_path: Path

    if repo_url.startswith(("http://", "https://", "git@")):
        target = settings.clone_path / uuid.uuid4().hex[:12]
        target.mkdir(parents=True, exist_ok=True)
        Repo.clone_from(repo_url, str(target), depth=1)
        repo_path = target
    else:
        repo_path = Path(repo_url).expanduser().resolve()
        if not repo_path.exists():
            raise FileNotFoundError(f"Local path does not exist: {repo_path}")

    dep_files = _detect_ecosystems(repo_path)
    ecosystems = list(dep_files.keys())

    return RepoInfo(
        path=repo_path,
        ecosystems=ecosystems,
        dependency_files=dep_files,
    )


def cleanup_repo(info: RepoInfo) -> None:
    """Remove a cloned repo directory."""
    settings = get_settings()
    if info.path.is_relative_to(settings.clone_path):
        shutil.rmtree(info.path, ignore_errors=True)
