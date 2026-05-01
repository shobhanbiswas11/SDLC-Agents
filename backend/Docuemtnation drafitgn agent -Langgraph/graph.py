"""
graph.py — LangGraph StateGraph for the Documentation Drafting Agent.

Replaces workflow.py (Temporal).
ReAct loop: gather_context → think → act → observe → repeat until final answer.

No Temporal server required.
State is persisted to a local SQLite file (checkpoints.db) — free, no cloud needed.

Graph structure:
    START → gather_context_node (once only) → llm_node → [tool_node → llm_node → ...] → END
"""

from __future__ import annotations

import sqlite3
from typing import Any, TypedDict

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from config_loader import load_all_config

# ── Load config once at startup ───────────────────────────────────────────────
SYSTEM_PROMPT, TOOL_SCHEMAS, TOOL_NAMES = load_all_config()

# SQLite path for state persistence (conversation survives restarts)
DB_PATH = "checkpoints.db"


# ── Agent State ───────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    """
    The full state of the agent — persisted automatically by LangGraph
    into SQLite after every node execution.
    """
    history:            list[dict]   # Full conversation history (OpenAI format)
    workspace_path:     str          # Root path of the workspace being documented
    repo_url:           str          # GitHub repo (owner/repo) if remote
    github_token:       str          # GitHub token for auth
    last_response:      str          # Last text response from the LLM
    status:             str          # "idle" | "thinking" | "gathering_context" | "waiting_for_user"
    navigated_file:     str          # Last file navigated to (for frontend)
    created_files:      list[str]    # Files created this session (for frontend)
    pending_tool_calls: list[dict]   # Tool calls requested by LLM, pending execution
    context_gathered:   bool         # True after first-turn RAG has run (skip on follow-ups)
    task_type:          str          # "qa" or "documentation"
    current_plan:       str          # The numbered plan for documentation tasks
    review_passed:      bool         # True once review_node approves the output
    review_attempts:    int          # Counter to prevent infinite review loops


# ── Routing Logic ─────────────────────────────────────────────────────────────

def route_after_gather(state: AgentState) -> str:
    """After gather_context_node, always go to task_classifier_node."""
    return "task_classifier_node"

def route_after_classify(state: AgentState) -> str:
    """Route based on whether the user wants Q&A or Documentation."""
    if state.get("task_type") == "qa":
        return "llm_node"
    return "planning_node"

def route_after_llm(state: AgentState) -> str:
    """
    After the LLM node runs, decide what to do next:
    - If the LLM requested tool calls → go to tool_node
    - If task_type is documentation → go to review_node
    - Otherwise (QA) → END
    """
    if state.get("pending_tool_calls"):
        return "tool_node"
    if state.get("task_type") == "documentation":
        return "review_node"
    return END

def route_after_review(state: AgentState) -> str:
    """
    After review_node runs:
    - If review passed (or max attempts reached) → END
    - If review failed → back to llm_node to fix
    """
    if state.get("review_passed"):
        return END
    return "llm_node"


import re as _re

_REINDEX_PATTERNS = _re.compile(
    r"\b(rescan|re-scan|re-?index|reindex|re-?analyz|reanalyz|look at .+ folder|switch to .+ folder|analyze .+ instead)",
    _re.IGNORECASE,
)


def route_entry(state: AgentState) -> str:
    """
    Entry routing:
    - If RAG context has NOT been gathered yet → gather_context_node.
    - If the user's latest message contains re-index keywords → gather_context_node (fresh scan).
    - Otherwise skip straight to llm_node.
    """
    if not state.get("context_gathered"):
        return "gather_context_node"
    # Check latest user message for re-index trigger words
    latest_query = ""
    for msg in reversed(state.get("history", [])):
        if msg.get("role") == "user":
            latest_query = msg.get("content", "")
            break
    if latest_query and _REINDEX_PATTERNS.search(latest_query):
        print("[graph] Re-index trigger detected — re-running RAG.")
        return "gather_context_node"
    return "task_classifier_node"


# ── Graph Builder ─────────────────────────────────────────────────────────────

def build_graph() -> Any:
    """
    Build and compile the LangGraph StateGraph.

    Graph structure:
        START → (route_entry) → gather_context_node → llm_node → [tool_node → llm_node → ...] → END

    The gather_context_node runs ONCE per session (guarded by context_gathered flag).
    On follow-up turns, the graph routes directly to llm_node.

    State is checkpointed to SQLite after every node.

    NOTE: In LangGraph 1.x, SqliteSaver requires a raw sqlite3 connection
    instance. check_same_thread=False allows use from the FastAPI async event loop.
    """
    from agent_node import (
        gather_context_node,
        task_classifier_node,
        planning_node,
        llm_node,
        tool_node,
        review_node
    )

    builder = StateGraph(AgentState)

    # Register nodes
    builder.add_node("gather_context_node",  gather_context_node)
    builder.add_node("task_classifier_node", task_classifier_node)
    builder.add_node("planning_node",        planning_node)
    builder.add_node("llm_node",             llm_node)
    builder.add_node("tool_node",            tool_node)
    builder.add_node("review_node",          review_node)

    # Entry point — route based on whether context has been gathered
    builder.set_conditional_entry_point(
        route_entry,
        {
            "gather_context_node":  "gather_context_node",
            "task_classifier_node": "task_classifier_node",
        }
    )

    # gather_context → task_classifier
    builder.add_edge("gather_context_node", "task_classifier_node")

    # task_classifier → planning OR llm
    builder.add_conditional_edges(
        "task_classifier_node",
        route_after_classify,
        {
            "llm_node":      "llm_node",
            "planning_node": "planning_node",
        }
    )

    # planning → llm
    builder.add_edge("planning_node", "llm_node")

    # After LLM: either call a tool, go to review, or finish
    builder.add_conditional_edges(
        "llm_node",
        route_after_llm,
        {
            "tool_node":   "tool_node",
            "review_node": "review_node",
            END:           END,
        }
    )

    # After tool execution: always loop back to LLM
    builder.add_edge("tool_node", "llm_node")

    # After review: either finish or loop back to LLM to fix issues
    builder.add_conditional_edges(
        "review_node",
        route_after_review,
        {
            "llm_node": "llm_node",
            END:        END,
        }
    )

    # Pass raw sqlite3 connection — required in LangGraph 1.x
    conn   = sqlite3.connect(DB_PATH, check_same_thread=False)
    memory = SqliteSaver(conn)

    return builder.compile(checkpointer=memory)


# ── Singleton graph instance ──────────────────────────────────────────────────
graph = build_graph()
