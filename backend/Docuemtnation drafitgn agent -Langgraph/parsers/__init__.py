"""
parsers — Codebase parsing utilities for the Documentation Drafting Agent.

Modules:
    tree_fetcher        : Fetch repository file trees (GitHub API + local filesystem)
    metadata_extractor  : Extract classes, functions, imports from multiple languages
    ast_graph_builder   : Build import/dependency graphs from source code
"""

from .tree_fetcher import fetch_tree_via_github_api, fetch_full_repo, fetch_local_repo
from .metadata_extractor import extract_all_metadata, format_metadata_block
from .ast_graph_builder import build_full_graph, build_file_index
