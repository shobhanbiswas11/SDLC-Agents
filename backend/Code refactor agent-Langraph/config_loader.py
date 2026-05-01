"""
config_loader.py — Backward-compatibility shim.

The real implementation lives in core/config_loader.py.
Any module that does `from config_loader import load_all_config` keeps working.

Do not add logic here — edit core/config_loader.py instead.
"""

from core.config_loader import (  # noqa: F401
    load_all_config,
    load_agent_config,
    load_tool_schemas,
    yaml_tool_to_openai_schema,
    CONFIG_DIR,
    TOOLS_DIR,
    AGENT_YAML,
)