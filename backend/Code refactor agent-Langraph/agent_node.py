"""
agent_node.py — Backward-compatibility shim.

The real implementations live in agent/nodes/ and agent/utils/.
Any module that does:
    from agent_node import _augment_message_with_github_paths
    from agent_node import llm_node, tool_node, ...
will continue to work via this shim.

Do not add logic here — edit the relevant agent/nodes/*.py files instead.
"""

# Public helpers that external code imports directly
from agent.utils.github_utils import augment_message_with_github_paths
# Legacy underscore name preserved for backward compat
_augment_message_with_github_paths = augment_message_with_github_paths

# Node functions
from agent.nodes.llm_node import llm_node                              # noqa: F401
from agent.nodes.tool_node import tool_node                             # noqa: F401
from agent.nodes.gather_context_node import gather_context_node         # noqa: F401
from agent.nodes.logic_verification_node import logic_verification_node # noqa: F401

# Utilities that may have been imported directly
from agent.utils.openai_client import get_openai_client as _get_openai_client  # noqa: F401
from agent.utils.history import trim_history as _trim_history                   # noqa: F401

# Config (previously loaded in this module)
from core.config_loader import load_all_config
SYSTEM_PROMPT, TOOL_SCHEMAS, TOOL_NAMES = load_all_config()
