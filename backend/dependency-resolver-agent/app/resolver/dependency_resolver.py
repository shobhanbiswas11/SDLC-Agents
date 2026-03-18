"""
Recursive dependency resolver — DFS with visited-set guard and concurrent fetching.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from app.metadata.npm_client import (
    extract_npm_dependencies,
    extract_npm_peer_dependencies,
    fetch_npm_metadata,
)
from app.metadata.pypi_client import extract_requires_dist, fetch_pypi_metadata
from app.parser.node_parser import Dependency as NodeDep
from app.parser.python_parser import Dependency as PyDep

logger = logging.getLogger(__name__)

# Simple regex to split PEP 508 strings coming from requires_dist
_PEP508_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9_.-]+)"
    r"(?:\[(?P<extras>[^\]]+)\])?"
    r"\s*(?P<spec>[><=!~][^;]*?)?"
    r"(?:\s*;.*)?$"
)

_NPM_VERSION_RE = re.compile(r"[\^~>=<]*([\d]+\.[\d]+\.[\d]+)")


@dataclass
class ResolvedNode:
    """Represents a single resolved dependency in the tree."""

    name: str
    version: str | None = None
    specifier: str = ""
    ecosystem: str = "python"
    children: dict[str, str] = field(default_factory=dict)  # child package name -> specifier
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResolutionResult:
    """Full resolution result for an ecosystem."""

    ecosystem: str
    root_dependencies: list[str] = field(default_factory=list)
    resolved: dict[str, ResolvedNode] = field(default_factory=dict)  # name → node
    errors: list[str] = field(default_factory=list)


# ── Python Resolver ──────────────────────────────────────────


async def _resolve_python_pkg(
    name: str,
    specifier: str,
    visited: set[str],
    resolved: dict[str, ResolvedNode],
    depth: int = 0,
    max_depth: int = 10,
) -> None:
    """Recursively resolve a Python package via PyPI."""
    normalised = name.lower().replace("-", "_").replace(".", "_")
    if normalised in visited or depth > max_depth:
        return
    visited.add(normalised)

    meta = await fetch_pypi_metadata(name)
    if meta is None:
        resolved[normalised] = ResolvedNode(
            name=name, specifier=specifier, ecosystem="python"
        )
        return

    version = meta.get("info", {}).get("version", "")
    requires = extract_requires_dist(meta)

    node = ResolvedNode(
        name=name,
        version=version,
        specifier=specifier,
        ecosystem="python",
        metadata={"requires_python": meta.get("info", {}).get("requires_python", "")},
    )

    # Parse children
    child_tasks = []
    for req_raw in requires:
        # Skip extras-only / environment markers that indicate optional
        if "extra ==" in req_raw:
            continue
        m = _PEP508_RE.match(req_raw.strip())
        if not m:
            continue
        child_name = m.group("name")
        child_spec = (m.group("spec") or "").strip()
        child_norm = child_name.lower().replace("-", "_").replace(".", "_")
        node.children[child_norm] = child_spec
        child_tasks.append(
            _resolve_python_pkg(child_name, child_spec, visited, resolved, depth + 1, max_depth)
        )

    resolved[normalised] = node

    if child_tasks:
        await asyncio.gather(*child_tasks)


async def resolve_python(deps: list[PyDep], max_depth: int = 10) -> ResolutionResult:
    """Resolve all Python root dependencies recursively."""
    visited: set[str] = set()
    resolved: dict[str, ResolvedNode] = {}
    root_names: list[str] = []

    tasks = []
    for dep in deps:
        norm = dep.name.lower().replace("-", "_").replace(".", "_")
        root_names.append(norm)
        tasks.append(
            _resolve_python_pkg(dep.name, dep.specifier, visited, resolved, max_depth=max_depth)
        )

    await asyncio.gather(*tasks)

    return ResolutionResult(
        ecosystem="python",
        root_dependencies=root_names,
        resolved=resolved,
    )


# ── Node Resolver ────────────────────────────────────────────


async def _resolve_node_pkg(
    name: str,
    specifier: str,
    visited: set[str],
    resolved: dict[str, ResolvedNode],
    depth: int = 0,
    max_depth: int = 10,
) -> None:
    """Recursively resolve an npm package via the npm registry."""
    if name in visited or depth > max_depth:
        return
    visited.add(name)

    # Try to get a specific version first
    version_match = _NPM_VERSION_RE.search(specifier)
    version = version_match.group(1) if version_match else None

    meta = await fetch_npm_metadata(name, version)
    if meta is None:
        # Try without version
        meta = await fetch_npm_metadata(name)
        if meta is None:
            resolved[name] = ResolvedNode(
                name=name, specifier=specifier, ecosystem="node"
            )
            return
        # Get latest version from dist-tags
        latest = meta.get("dist-tags", {}).get("latest")
        if latest and "versions" in meta:
            meta = meta.get("versions", {}).get(latest, meta)

    actual_version = meta.get("version", "")
    child_deps = extract_npm_dependencies(meta)
    peer_deps = extract_npm_peer_dependencies(meta)

    node = ResolvedNode(
        name=name,
        version=actual_version,
        specifier=specifier,
        ecosystem="node",
    )

    child_tasks = []
    all_deps = {**child_deps, **peer_deps}
    for child_name, child_spec in all_deps.items():
        node.children[child_name] = child_spec
        child_tasks.append(
            _resolve_node_pkg(child_name, child_spec, visited, resolved, depth + 1, max_depth)
        )

    resolved[name] = node

    if child_tasks:
        await asyncio.gather(*child_tasks)


async def resolve_node(deps: list[NodeDep], max_depth: int = 10) -> ResolutionResult:
    """Resolve all Node root dependencies recursively."""
    visited: set[str] = set()
    resolved: dict[str, ResolvedNode] = {}
    root_names: list[str] = []

    tasks = []
    for dep in deps:
        root_names.append(dep.name)
        tasks.append(
            _resolve_node_pkg(dep.name, dep.specifier, visited, resolved, max_depth=max_depth)
        )

    await asyncio.gather(*tasks)

    return ResolutionResult(
        ecosystem="node",
        root_dependencies=root_names,
        resolved=resolved,
    )
