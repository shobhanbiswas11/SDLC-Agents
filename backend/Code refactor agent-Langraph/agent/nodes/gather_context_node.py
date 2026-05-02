"""
agent/nodes/gather_context_node.py — LangGraph node: RAG pre-processing.

Runs at the very start of a session (``context_gathered=False``) and injects
a structured codebase snapshot into the conversation history so the LLM has
rich workspace context before the user's first instruction is processed.

The node is skipped on all subsequent turns (``context_gathered=True``).
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from agent.state import AgentState
from core.logging import get_logger

logger = get_logger(__name__)

_MAX_SNIPPET_CHARS = 4_000
_MAX_RANKED_FILES = 20
_MAX_TREE_ITEMS = 100


def _repo_workspace_path(owner: str, repo: str) -> str:
    """Return a materialized repo path outside the uvicorn reload watch tree."""
    base = os.getenv("REFACTOR_REPOS_DIR")
    root = Path(base).expanduser() if base else Path.home() / ".cache" / "code_refactor_agent" / "repos"
    return str((root / owner / repo).resolve())


def _materialize_repo_files(workspace_path: str, file_map: dict[str, str]) -> None:
    """Write fetched GitHub files to disk so local refactor tools can operate."""
    root = Path(workspace_path).resolve()
    root.mkdir(parents=True, exist_ok=True)
    for rel_path, content in file_map.items():
        if content is None:
            continue
        target = (root / rel_path).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            logger.warning("gather_context: skipped unsafe GitHub path %s", rel_path)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def _smart_snippet(content: str, max_chars: int = _MAX_SNIPPET_CHARS) -> str:
    """Return first 65% + last 35% of allowed chars to capture both header and tail."""
    if len(content) <= max_chars:
        return content
    head_len = int(max_chars * 0.65)
    tail_len = max_chars - head_len
    return content[:head_len] + "\n...\n" + content[-tail_len:]


async def gather_context_node(state: AgentState) -> dict:
    """
    Build a codebase context string via the RAG pipeline and inject it as a
    system message into the conversation history.

    Steps:
    1. Fetch the file tree and contents (local or GitHub).
    2. Extract metadata (imports, exports, class/function signatures).
    3. Build a dependency graph and rank files by importance.
    4. Format and inject the context as a ``system`` message.

    Sets ``context_gathered=True`` so this node is not re-entered on
    follow-up turns.
    """
    workspace_path: str = state.get("workspace_path", ".")
    history = list(state.get("history", []))

    context_str = f"Codebase Context ({workspace_path}):\n"
    file_map: dict[str, str] = {}
    file_tree: list[str] = []

    try:
        from parsers.tree_fetcher import (
            fetch_local_repo,
            fetch_full_repo,
            normalize_github_repo,
        )
        from parsers.metadata_extractor import extract_all_metadata, format_metadata_block
        from parsers.ast_graph_builder import build_combined_graph
        from intelligence.file_ranker import rank_files

        if state.get("repo_url"):
            repo_url = state["repo_url"]
            token = state.get("github_token", "")
            branch = state.get("github_branch", "main")

            logger.info("gather_context: fetching GitHub repo %s@%s", repo_url, branch)
            file_map, file_tree = await asyncio.to_thread(
                fetch_full_repo, repo_url, token, branch
            )

            owner, repo = normalize_github_repo(repo_url)
            workspace_path = _repo_workspace_path(owner, repo)
            await asyncio.to_thread(_materialize_repo_files, workspace_path, file_map)

        elif not os.path.exists(workspace_path):
            logger.warning("gather_context: workspace '%s' does not exist", workspace_path)
            context_str += f"Warning: workspace '{workspace_path}' does not exist.\n"

        else:
            logger.info("gather_context: scanning local workspace %s", workspace_path)
            file_map, file_tree = await asyncio.to_thread(fetch_local_repo, workspace_path)

        if not file_tree:
            context_str += "No files found in workspace or GitHub repository.\n"
        else:
            try:
                cached_metadata = await asyncio.to_thread(extract_all_metadata, file_map)
                metadata_block = format_metadata_block(cached_metadata)
            except Exception as exc:
                logger.warning("gather_context: metadata extraction failed: %s", exc)
                metadata_block = "Metadata unavailable."

            try:
                dep_graph = await asyncio.to_thread(build_combined_graph, file_map)
                ranked = await asyncio.to_thread(
                    rank_files, file_map, file_tree, dep_graph, _MAX_RANKED_FILES, False
                )
            except Exception as exc:
                logger.warning("gather_context: ranking failed: %s", exc)
                ranked = [(p, 1.0) for p in list(file_map.keys())[:_MAX_RANKED_FILES]]

            tree_sample = "\n".join(file_tree[:_MAX_TREE_ITEMS])
            context_str += f"Tree (first {_MAX_TREE_ITEMS} items):\n{tree_sample}\n\n"
            context_str += f"Metadata:\n{metadata_block}\n\n"
            context_str += "Top Relevant Files:\n"
            for path, _ in ranked:
                if path in file_map:
                    context_str += f"\n--- {path} ---\n{_smart_snippet(file_map[path])}\n"

    except ImportError as exc:
        logger.warning("gather_context: RAG modules unavailable (%s)", exc)
        context_str += (
            f"Warning: Could not load RAG modules ({exc}). "
            "Running without pre-gathered context.\n"
        )
    except Exception as exc:
        logger.exception("gather_context: RAG pipeline failed")
        context_str += f"Warning: RAG pipeline failed ({exc}). Continuing without context.\n"

    # Inject context right after the first system message
    system_injection = {
        "role": "system",
        "content": f"PRE-GATHERED RAG CONTEXT:\n{context_str}",
    }
    updated_history: list[dict] = []
    injected = False
    for msg in history:
        updated_history.append(msg)
        if msg.get("role") == "system" and not injected:
            updated_history.append(system_injection)
            injected = True
    if not injected:
        updated_history.insert(0, system_injection)

    logger.info("gather_context: context injected (%d chars)", len(context_str))

    return {
        **state,
        "history": updated_history,
        "workspace_path": workspace_path,
        "context_gathered": True,
        "status": "thinking",
    }
