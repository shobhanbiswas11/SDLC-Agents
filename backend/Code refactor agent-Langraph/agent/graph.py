"""
agent/graph.py — LangGraph StateGraph builder for the Code Refactoring Agent.

This module exports a single function, ``build_graph()``, which returns an
*uncompiled* ``StateGraph``. The caller (``app/api.py`` or ``app/cli.py``)
is responsible for attaching a checkpointer and calling ``.compile()``.

This separation eliminates the sync/async SQLite conflict that arose when
``graph.py`` used to instantiate a ``SqliteSaver`` singleton — async callers
(FastAPI) need ``AsyncSqliteSaver`` while the sync CLI needs ``SqliteSaver``.

Graph topology
--------------
                ┌──────────────────┐
    START ──►  │ gather_context    │ (first turn only)
                └───────┬──────────┘
                        │
                        ▼
               ┌─────────────────┐
    ┌────────► │   llm_node      │ ◄──────────────────────────┐
    │           └───────┬─────────┘                            │
    │                   │ tool calls?                          │
    │           ┌───────▼─────────┐                           │
    │           │   tool_node     │ ──────────────────────────┘
    │           └─────────────────┘
    │
    │           final answer
    │           ┌──────────────────────┐
    └────────── │ logic_verification   │ ──► END (approved)
                └──────────────────────┘
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from agent.state import AgentState


# ── Routing helpers ────────────────────────────────────────────────────────────

def _route_entry(state: AgentState) -> str:
    """First node: run context gathering on turn 1, skip on subsequent turns."""
    return "gather_context_node" if not state.get("context_gathered") else "llm_node"


def _route_after_llm(state: AgentState) -> str:
    """After LLM: call a tool if requested, otherwise run logic verification."""
    return "tool_node" if state.get("pending_tool_calls") else "logic_verification_node"


def _route_after_tool(state: AgentState) -> str:
    """After tools: end immediately for terminal tools like GitHub push."""
    return END if state.get("finalize_after_tool") else "llm_node"


def _route_after_verification(state: AgentState) -> str:
    """After verification: finish if approved, re-enter LLM if rejected."""
    return END if state.get("verification_passed") else "llm_node"


# ── Builder ────────────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Build and return the uncompiled LangGraph ``StateGraph``.

    The caller must compile it with a checkpointer before use:

        builder = build_graph()
        graph = builder.compile(checkpointer=my_saver)
    """
    # Deferred imports prevent circular dependencies at module load time
    from agent.nodes.gather_context_node import gather_context_node
    from agent.nodes.llm_node import llm_node
    from agent.nodes.tool_node import tool_node
    from agent.nodes.logic_verification_node import logic_verification_node

    g = StateGraph(AgentState)

    # Register nodes
    g.add_node("gather_context_node", gather_context_node)
    g.add_node("llm_node", llm_node)
    g.add_node("tool_node", tool_node)
    g.add_node("logic_verification_node", logic_verification_node)

    # Entry point (conditional: context vs. llm)
    g.set_conditional_entry_point(
        _route_entry,
        {
            "gather_context_node": "gather_context_node",
            "llm_node": "llm_node",
        },
    )

    # gather_context → llm_node (always)
    g.add_conditional_edges(
        "gather_context_node",
        lambda s: "llm_node",
        {"llm_node": "llm_node"},
    )

    # llm_node → tool_node | logic_verification_node
    g.add_conditional_edges(
        "llm_node",
        _route_after_llm,
        {
            "tool_node": "tool_node",
            "logic_verification_node": "logic_verification_node",
        },
    )

    # tool_node → END for terminal tool results, otherwise continue ReAct loop
    g.add_conditional_edges(
        "tool_node",
        _route_after_tool,
        {
            "llm_node": "llm_node",
            END: END,
        },
    )

    # logic_verification_node → END | llm_node
    g.add_conditional_edges(
        "logic_verification_node",
        _route_after_verification,
        {
            "llm_node": "llm_node",
            END: END,
        },
    )

    return g
