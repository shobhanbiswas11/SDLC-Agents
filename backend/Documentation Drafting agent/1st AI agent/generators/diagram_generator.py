# repo_summarizer/diagram_generator.py
"""
Mermaid Architecture Diagram Generator

Converts the import/dependency graph (built by ast_graph_builder.py) into a
Mermaid flowchart TD diagram. The diagram is embedded in the generated README
under an `## Architecture` section.

Usage:
    from generators.diagram_generator import build_mermaid_diagram
    mermaid_str = build_mermaid_diagram(graph, file_tree, top_k=15)
"""

import re
import posixpath
from collections import Counter
from typing import Dict, Set, List, Optional


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_node_id(path: str) -> str:
    """
    Convert a file path into a safe Mermaid node identifier.
    e.g. 'src/api/routes.py' -> 'src_api_routes_py'
    """
    return re.sub(r'[^a-zA-Z0-9]', '_', path)


def _short_label(path: str) -> str:
    """
    Return a readable short label for a node.
    e.g. 'src/api/routes.py' -> 'routes.py'
         'app/models/user.js' -> 'models/user.js'
    """
    parts = path.split("/")
    if len(parts) <= 2:
        return path
    # Show last two parts for clarity
    return "/".join(parts[-2:])


def _compute_node_importance(
    graph: Dict[str, Set[str]],
) -> Dict[str, int]:
    """
    Compute importance as in-degree + out-degree for each node.
    Higher = more central to the codebase.
    """
    importance: Dict[str, int] = {}
    # Out-degree
    for path, deps in graph.items():
        importance[path] = importance.get(path, 0) + len(deps)
    # In-degree
    for path, deps in graph.items():
        for dep in deps:
            importance[dep] = importance.get(dep, 0) + 1
    return importance


# ── Skip list  ────────────────────────────────────────────────────────────────

_SKIP_STEMS = {
    "__init__", "index", "conftest", "setup", "migrate",
    "manage", "wsgi", "asgi",
}

_SKIP_DIRS = {
    "tests", "test", "__pycache__", "node_modules", "dist",
    "build", ".next", "migrations",
}


def _should_skip_in_diagram(path: str) -> bool:
    parts = path.lower().split("/")
    for p in parts:
        if p in _SKIP_DIRS:
            return True
    stem = posixpath.basename(path).split(".")[0].lower()
    return stem in _SKIP_STEMS


# ── Main builder ──────────────────────────────────────────────────────────────

def build_mermaid_diagram(
    graph: Dict[str, Set[str]],
    file_tree: List[str],
    top_k: int = 15,
    max_edges: int = 30,
) -> str:
    """
    Build a Mermaid flowchart TD string from the import graph.

    Args:
        graph:     {source_file: {imported_file, ...}} from ast_graph_builder.
        file_tree: Full list of repo file paths (for fallback if graph is sparse).
        top_k:     Max number of nodes to include.
        max_edges: Max number of edges to include (keeps diagram readable).

    Returns:
        A Mermaid flowchart TD string ready to embed in markdown as:
            ```mermaid
            flowchart TD
                ...
            ```
    """
    if not graph:
        return ""

    # ── 1. Select top-k most important nodes ──────────────────────────────────
    importance = _compute_node_importance(graph)

    # Filter out trivial / skip files
    filtered = {
        path: score
        for path, score in importance.items()
        if not _should_skip_in_diagram(path)
    }

    # Sort by importance descending, take top_k
    top_nodes = set(
        path for path, _ in
        sorted(filtered.items(), key=lambda x: x[1], reverse=True)[:top_k]
    )

    # ── 2. Collect edges between top nodes only ────────────────────────────────
    edges: List[tuple] = []
    for src, deps in graph.items():
        if src not in top_nodes:
            continue
        if _should_skip_in_diagram(src):
            continue
        for dep in deps:
            if dep not in top_nodes:
                continue
            if _should_skip_in_diagram(dep):
                continue
            if src != dep:  # no self-loops
                edges.append((src, dep))

    # If graph is very sparse, fall back to showing nodes alone (no edges)
    edge_count = min(len(edges), max_edges)
    trimmed_edges = edges[:edge_count]

    # ── 3. Build the Mermaid string ───────────────────────────────────────────
    if not top_nodes and not trimmed_edges:
        return ""

    lines = ["flowchart TD"]

    # Define nodes with labels
    defined_nodes: set = set()
    for path in sorted(top_nodes):
        node_id = _safe_node_id(path)
        label = _short_label(path)
        lines.append(f'    {node_id}["{label}"]')
        defined_nodes.add(path)

    if trimmed_edges:
        lines.append("")  # blank line for readability

    # Define edges
    for src, dep in trimmed_edges:
        src_id = _safe_node_id(src)
        dep_id = _safe_node_id(dep)
        lines.append(f"    {src_id} --> {dep_id}")

    # ── 4. Add style classes for visual grouping ───────────────────────────────
    lines.append("")
    lines.append("    classDef backend fill:#1a1a2e,stroke:#7c6cf8,color:#e8eaf6")
    lines.append("    classDef frontend fill:#0d1b2a,stroke:#00e8a2,color:#e8eaf6")
    lines.append("    classDef config fill:#1a0a0a,stroke:#f5a623,color:#e8eaf6")

    # Apply classes based on file extension / folder
    for path in sorted(top_nodes):
        node_id = _safe_node_id(path)
        p_lower = path.lower()
        if any(p_lower.endswith(ext) for ext in (".ts", ".tsx", ".jsx", ".css", ".scss", ".html", ".vue", ".svelte")):
            lines.append(f"    class {node_id} frontend")
        elif any(p_lower.endswith(ext) for ext in (".json", ".yaml", ".yml", ".toml", ".ini", ".env")):
            lines.append(f"    class {node_id} config")
        else:
            lines.append(f"    class {node_id} backend")

    return "\n".join(lines)


def format_diagram_for_readme(mermaid_str: str) -> str:
    """
    Wrap a Mermaid string in a proper README section block.

    Returns:
        A markdown string ready to inject into the README.
    """
    if not mermaid_str:
        return ""
    return f"""## Architecture

The following diagram shows the dependency relationships between the main modules of this project:

```mermaid
{mermaid_str}
```
"""


def build_diagram_summary(graph: Dict[str, Set[str]]) -> dict:
    """
    Return a JSON-serialisable summary of the diagram for API responses.

    Returns:
        {
            "node_count": int,
            "edge_count": int,
            "mermaid": str,
            "top_nodes": [str, ...]
        }
    """
    importance = _compute_node_importance(graph)
    mermaid_str = build_mermaid_diagram(graph, list(importance.keys()))
    top_nodes = [
        path for path, _ in
        sorted(importance.items(), key=lambda x: x[1], reverse=True)[:15]
        if not _should_skip_in_diagram(path)
    ]

    edge_count = sum(len(deps) for deps in graph.values())

    return {
        "node_count": len(importance),
        "edge_count": edge_count,
        "mermaid": mermaid_str,
        "top_nodes": top_nodes,
    }
