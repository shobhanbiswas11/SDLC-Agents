"""
DAG builder for dependency graphs.
Constructs the full transitive dependency tree and detects cycles.
"""
from __future__ import annotations
import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from agents.dependency_resolver.registry import get_registry

logger = logging.getLogger(__name__)


class DependencyNode:
    __slots__ = ("name", "constraint", "version", "parents", "children",
                 "license", "direct", "error")

    def __init__(self, name: str, constraint: str, direct: bool = False):
        self.name       = name
        self.constraint = constraint
        self.version: Optional[str]     = None
        self.parents: List[str]         = []
        self.children: List[str]        = []
        self.license: Optional[str]     = None
        self.direct                     = direct
        self.error: Optional[str]       = None


class DependencyGraph:
    """Builds and holds the full transitive dependency DAG."""

    def __init__(self, ecosystem: str, max_depth: int = 4):
        self.ecosystem  = ecosystem
        self.max_depth  = max_depth
        self.registry   = get_registry(ecosystem)
        self.nodes: Dict[str, DependencyNode] = {}
        self.errors: List[str] = []

    async def build(
        self,
        direct: List[Tuple[str, str]],
        include_dev: bool = False,
    ) -> None:
        visited: Set[str] = set()
        for name, constraint in direct:
            node = DependencyNode(name, constraint, direct=True)
            self.nodes[name] = node
            await self._expand(name, constraint, depth=0, visited=visited)

    async def _expand(
        self,
        name: str,
        constraint: str,
        depth: int,
        visited: Set[str],
        parent: Optional[str] = None,
    ) -> None:
        if depth > self.max_depth:
            return

        node = self.nodes.setdefault(name, DependencyNode(name, constraint))
        if parent and parent not in node.parents:
            node.parents.append(parent)

        if name in visited:
            return
        visited.add(name)

        try:
            version = await self.registry.find_compatible_version(name, constraint)
            if not version:
                msg = f"No compatible version for {name} constraint={constraint}"
                logger.warning(msg)
                node.error = msg
                self.errors.append(msg)
                return

            node.version = version

            sub_deps = await self.registry.get_dependencies(name, version)
            for sub_name, sub_constraint in sub_deps.items():
                if sub_name not in node.children:
                    node.children.append(sub_name)
                await self._expand(sub_name, sub_constraint,
                                   depth + 1, visited, parent=name)

        except Exception as exc:
            msg = f"Error expanding {name}: {exc}"
            logger.error(msg)
            node.error = msg
            self.errors.append(msg)

    def detect_cycles(self) -> List[List[str]]:
        """Return list of cycle paths found in the DAG."""
        cycles: List[List[str]] = []
        visited: Set[str] = set()
        path: List[str] = []

        def dfs(node: str) -> None:
            if node in path:
                idx = path.index(node)
                cycles.append(path[idx:] + [node])
                return
            if node in visited:
                return
            visited.add(node)
            path.append(node)
            for child in self.nodes.get(node, DependencyNode(node, "*")).children:
                dfs(child)
            path.pop()

        for name in self.nodes:
            dfs(name)
        return cycles

    def to_dict(self) -> Dict[str, Any]:
        return {
            name: {
                "version":    node.version,
                "constraint": node.constraint,
                "direct":     node.direct,
                "parents":    node.parents,
                "children":   node.children,
                "license":    node.license,
                "error":      node.error,
            }
            for name, node in self.nodes.items()
        }
