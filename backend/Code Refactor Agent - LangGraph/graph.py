"""
graph.py — LangGraph StateGraph for the Code Refactoring Agent.

Replaces workflow.py (Temporal).
ReAct loop: think → act → observe → repeat until the LLM gives a final answer.

No Temporal server required.
State is persisted to a local SQLite file (checkpoints.db) — free, no cloud needed.
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
    history: list[dict]             # Full conversation history (OpenAI format)
    workspace_path: str             # Root path of the workspace being refactored
    last_response: str              # Last text response from the LLM
    status: str                     # "idle" | "thinking" | "waiting_for_user"
    navigated_file: str             # Last file navigated to (for frontend)
    created_files: list[str]        # Files created this session (for frontend)
    pending_tool_calls: list[dict]  # Tool calls requested by LLM, pending execution


# ── Routing Logic ─────────────────────────────────────────────────────────────

def route_after_llm(state: AgentState) -> str:
    """
    After the LLM node runs, decide what to do next:
    - If the LLM requested tool calls → go to tool_node
    - If the LLM gave a final text answer → END
    """
    if state.get("pending_tool_calls"):
        return "tool_node"
    return END


# ── Graph Builder ─────────────────────────────────────────────────────────────

def build_graph() -> Any:
    """
    Build and compile the LangGraph StateGraph.

    Graph structure:
        START -> llm_node -> [tool_node -> llm_node -> ...] -> END

    The loop continues until the LLM stops requesting tools.
    State is checkpointed to SQLite after every node.

    NOTE: In LangGraph 1.x, SqliteSaver requires a raw sqlite3 connection
    instance. SqliteSaver.from_conn_string() returns a context manager and
    cannot be passed directly to compile().
    """
    from agent_node import llm_node, tool_node

    builder = StateGraph(AgentState)

    # Register nodes
    builder.add_node("llm_node",  llm_node)
    builder.add_node("tool_node", tool_node)

    # Entry point
    builder.set_entry_point("llm_node")

    # After LLM: either call a tool or finish
    builder.add_conditional_edges(
        "llm_node",
        route_after_llm,
        {
            "tool_node": "tool_node",
            END: END,
        }
    )

    # After tool execution: always loop back to LLM
    builder.add_edge("tool_node", "llm_node")

    # Pass raw sqlite3 connection — required in LangGraph 1.x
    # check_same_thread=False allows use from the FastAPI async event loop
    conn   = sqlite3.connect(DB_PATH, check_same_thread=False)
    memory = SqliteSaver(conn)

    return builder.compile(checkpointer=memory)


# ── Singleton graph instance ──────────────────────────────────────────────────
graph = build_graph()
