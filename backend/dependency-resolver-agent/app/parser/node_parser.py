"""
Node.js dependency parser — handles package.json.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Dependency:
    """A single parsed npm dependency."""

    name: str
    specifier: str = ""  # e.g. "^1.0.0"
    dep_type: str = "dependencies"  # dependencies | devDependencies | peerDependencies
    source_file: str = ""
    ecosystem: str = "node"


def _parse_package_json(path: Path) -> list[Dependency]:
    data = json.loads(path.read_text(encoding="utf-8"))
    deps: list[Dependency] = []

    for section in ("dependencies", "devDependencies", "peerDependencies"):
        for name, spec in data.get(section, {}).items():
            deps.append(
                Dependency(
                    name=name,
                    specifier=spec,
                    dep_type=section,
                    source_file=str(path),
                )
            )
    return deps


def parse_node_deps(paths: list[Path]) -> list[Dependency]:
    """
    Parse all Node dependency files and return a flat list of Dependency objects.
    """
    all_deps: list[Dependency] = []
    for p in paths:
        if p.name == "package.json":
            all_deps.extend(_parse_package_json(p))
    return all_deps
