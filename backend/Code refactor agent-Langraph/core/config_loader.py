"""
core/config_loader.py — Reads YAML config files and converts them to OpenAI tool schemas.

Reads config/agent.yaml for the system prompt and tool list,
then loads each tool's YAML from config/tools/ and converts to OpenAI format.
"""

from pathlib import Path
from typing import Any

import yaml

# Resolve paths relative to THIS file so imports work from any working directory
_CORE_DIR = Path(__file__).parent
_BACKEND_DIR = _CORE_DIR.parent
CONFIG_DIR = _BACKEND_DIR / "config"
TOOLS_DIR = CONFIG_DIR / "tools"
AGENT_YAML = CONFIG_DIR / "agent.yaml"


def load_agent_config() -> dict[str, Any]:
    """Load config/agent.yaml and return the full dict."""
    with open(AGENT_YAML, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    data.setdefault("system_prompt", "You are a helpful AI assistant.")
    return data


def yaml_tool_to_openai_schema(tool_data: dict[str, Any]) -> dict[str, Any]:
    """Convert a single tool YAML dict into OpenAI function-calling format."""
    name = tool_data["name"]
    description = tool_data.get("description", "").strip()
    raw_params = tool_data.get("parameters", {"type": "object", "properties": {}})

    properties: dict[str, Any] = {}
    for param_name, param_data in raw_params.get("properties", {}).items():
        prop = {k: v for k, v in param_data.items() if k != "default"}
        prop.setdefault("type", "string")
        properties[param_name] = prop

    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": raw_params.get("required", []),
            },
        },
    }


def load_tool_schemas(tool_names: list[str]) -> list[dict[str, Any]]:
    """Load tool schemas from YAML files for the given tool names."""
    schemas: list[dict[str, Any]] = []
    for tool_name in tool_names:
        yaml_path = TOOLS_DIR / f"{tool_name}.yaml"
        if not yaml_path.exists():
            print(f"[config_loader] WARNING: {yaml_path} not found, skipping")
            continue
        with open(yaml_path, "r", encoding="utf-8") as f:
            tool_data = yaml.safe_load(f)
        schemas.append(yaml_tool_to_openai_schema(tool_data))
    return schemas


def load_all_config() -> tuple[str, list[dict[str, Any]], list[str]]:
    """
    One-shot loader.

    Returns:
        (system_prompt, tool_schemas, tool_names)
    """
    agent_config = load_agent_config()
    tool_names: list[str] = agent_config.get("tools", [])
    tool_schemas = load_tool_schemas(tool_names)
    system_prompt: str = agent_config.get("system_prompt", "You are a helpful AI assistant.")
    print(f"[config_loader] Agent: {agent_config.get('name', 'Unknown')}")
    print(f"[config_loader] Loaded {len(tool_schemas)} tools: {[t['function']['name'] for t in tool_schemas]}")
    return system_prompt, tool_schemas, tool_names
