"""
agent/state.py — Single source of truth for the AgentState TypedDict.

All LangGraph nodes and routing functions import AgentState from here.
This eliminates circular imports and keeps the type contract in one place.
"""

from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict):
    """
    The full persisted state of the Code Refactoring Agent.

    LangGraph checkpoints this dict to SQLite after every node execution,
    so a session survives restarts and can be resumed across turns.

    Fields
    ------
    history : list[dict]
        Full conversation history in OpenAI message format.
    workspace_path : str
        Root directory of the codebase being refactored.
    repo_url : str
        Optional GitHub repository URL (GitHub-backed sessions).
    github_branch : str
        Branch to use when cloning from GitHub.
    github_token : str
        Personal access token for private GitHub repositories.
    last_response : str
        The most recent text response produced by the LLM.
    status : str
        Current lifecycle state: "idle" | "thinking" | "waiting_for_user".
    navigated_file : str
        Last file navigated to — surfaced to the frontend for editor focus.
    created_files : list[str]
        Files created during this session — surfaced to the frontend.
    pending_tool_calls : list[dict]
        Tool calls requested by the LLM that are awaiting execution.
    context_gathered : bool
        True once the first-turn RAG pre-processing has completed.
    verification_passed : bool
        True once logic_verification_node has approved the current refactor.
    verification_attempts : int
        Number of logic verification retries performed this turn.
    finalize_after_tool : bool
        True when a terminal tool result should end the graph immediately.
    """

    history: list[dict]
    workspace_path: str
    repo_url: str
    github_branch: str
    github_token: str
    last_response: str
    status: str
    navigated_file: str
    created_files: list[str]
    pending_tool_calls: list[dict]
    context_gathered: bool
    verification_passed: bool
    verification_attempts: int
    finalize_after_tool: bool
