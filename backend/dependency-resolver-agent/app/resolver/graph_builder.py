"""
Graph builder — construct a networkx DiGraph from resolution results.
"""

from __future__ import annotations

from typing import Any

import networkx as nx

from app.resolver.dependency_resolver import ResolutionResult


def build_graph(result: ResolutionResult) -> nx.DiGraph:
    """
    Build a directed graph from a ResolutionResult.

    Nodes carry attributes: version, specifier, ecosystem.
    Edges go from parent → child.
    """
    G = nx.DiGraph()

    for name, node in result.resolved.items():
        G.add_node(
            name,
            version=node.version or "",
            specifier=node.specifier,
            ecosystem=node.ecosystem,
        )
        for child, spec in node.children.items():
            G.add_edge(name, child, specifier=spec)

    return G


def graph_to_dict(G: nx.DiGraph) -> dict[str, Any]:
    """
    Serialise a networkx DiGraph to a JSON-friendly dict.

    Format:
    {
        "nodes": [{"id": "pkg", "version": "1.0", ...}, ...],
        "edges": [{"source": "a", "target": "b"}, ...]
    }
    """
    nodes = []
    for n, attrs in G.nodes(data=True):
        nodes.append({"id": n, **attrs})

    edges = [{"source": u, "target": v} for u, v in G.edges()]

    return {"nodes": nodes, "edges": edges}


def detect_cycles(G: nx.DiGraph) -> list[list[str]]:
    """Return all simple cycles in the graph."""
    try:
        return list(nx.simple_cycles(G))
    except nx.NetworkXError:
        return []


def get_dependency_tree(G: nx.DiGraph, root: str, depth: int = 0, max_depth: int = 8) -> dict:
    """
    Build a nested tree dict from a root node.
    """
    if depth > max_depth or root not in G:
        return {"name": root, "children": []}

    children = []
    for child in G.successors(root):
        children.append(get_dependency_tree(G, child, depth + 1, max_depth))

    node_data = G.nodes.get(root, {})
    return {
        "name": root,
        "version": node_data.get("version", ""),
        "children": children,
    }
