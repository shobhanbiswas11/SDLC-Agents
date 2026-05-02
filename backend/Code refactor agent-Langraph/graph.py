"""
graph.py — Backward-compatibility shim.

The real implementation lives in agent/graph.py.

Any module that does `from graph import graph, SYSTEM_PROMPT, builder`
will continue to work via this shim. The compiled `graph` here intentionally
does not attach a SQLite checkpointer; app/api.py owns production checkpointing
with AsyncSqliteSaver.
Do not add logic here — edit agent/graph.py instead.
"""

from agent.graph import build_graph
from core.config_loader import load_all_config

# Re-export SYSTEM_PROMPT for any existing imports
SYSTEM_PROMPT, _, _ = load_all_config()

# builder — uncompiled StateGraph (used by app/api.py in the old import style)
builder = build_graph()

# graph — compatibility-only compiled graph without persistent checkpointing.
graph = builder.compile()
