"""
config_loader.py — Reads YAML config files and converts them to OpenAI tool schemas.

This is the ONLY place that knows about YAML. 
Everything else just sees plain Python dicts and lists.

How YAML → OpenAI schema conversion works:
  Your YAML file has:
    name: read_file
    description: "Read a file..."
    parameters:
      type: object
      properties:
        file_path:
          type: string
          description: "..."
      required: [file_path]

  OpenAI needs:
    {
      "type": "function",
      "function": {
        "name": "read_file",
        "description": "Read a file...",
        "parameters": {
          "type": "object",
          "properties": { "file_path": {"type": "string", "description": "..."} },
          "required": ["file_path"]
        }
      }
    }

  This file does that exact conversion.
"""

import os
from pathlib import Path
from typing import Any

import yaml


# ──────────────────────────────────────────────
# PATHS
# ──────────────────────────────────────────────

CONFIG_DIR = Path(__file__).parent / "config"
TOOLS_DIR = CONFIG_DIR / "tools"
AGENT_YAML = CONFIG_DIR / "agent.yaml"


# ──────────────────────────────────────────────
# YAML LOADERS
# ──────────────────────────────────────────────

def load_agent_config() -> dict[str, Any]:
    """
    Load the agent YAML file (config/agent.yaml).
    Returns a dict with: system_prompt, tools (list of tool names), id, name, etc.
    """
    with open(AGENT_YAML, "r") as f:
        data = yaml.safe_load(f)

    # Expand any {variable} placeholders in the system prompt
    system_prompt = data.get("system_prompt", "You are a helpful AI assistant.")
    system_prompt = system_prompt.replace("{available_agents}", "None. You are the only agent.")
    system_prompt = system_prompt.replace("{agent_name}", data.get("name", "Universal Agent"))

    data["system_prompt"] = system_prompt
    return data


def yaml_tool_to_openai_schema(tool_data: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a single tool's YAML dict into an OpenAI function calling schema dict.
    
    Only extracts 'name', 'description', and 'parameters' from the YAML.
    All other fields (like 'activity') are ignored.
    
    NOTE: Tool routing is handled by the TOOL_HANDLERS dict in tools.py,
    which maps tool names to their Python handler functions.
    """
    # Pull out the OpenAI-relevant fields from the YAML
    name = tool_data["name"]
    description = tool_data.get("description", "").strip()
    raw_params = tool_data.get("parameters", {"type": "object", "properties": {}})

    # Build clean parameters block (remove 'default' fields — OpenAI doesn't use them)
    properties = {}
    for param_name, param_data in raw_params.get("properties", {}).items():
        prop = {}
        for k, v in param_data.items():
            if k == "default":
                continue
            prop[k] = v
            
        if "type" not in prop:
            prop["type"] = "string"
            
        properties[param_name] = prop

    openai_schema = {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": raw_params.get("required", []),
            }
        }
    }

    return openai_schema


def load_tool_schemas(tool_names: list[str]) -> list[dict[str, Any]]:
    """
    Load tool schemas from YAML files for the given list of tool names.
    
    Args:
        tool_names: List of tool names to load (from the agent's 'tools:' list).
                    E.g. ["read_file", "github_inline_comment", "ask_user"]
    
    Returns:
        List of OpenAI-formatted tool schema dicts, ready to pass to the API.
    """
    schemas = []
    missing = []

    for tool_name in tool_names:
        yaml_path = TOOLS_DIR / f"{tool_name}.yaml"

        if not yaml_path.exists():
            missing.append(tool_name)
            continue

        with open(yaml_path, "r") as f:
            tool_data = yaml.safe_load(f)

        schema = yaml_tool_to_openai_schema(tool_data)
        schemas.append(schema)

    if missing:
        print(f"[config_loader] WARNING: YAML files not found for tools: {missing}")

    return schemas


def load_all_config() -> tuple[str, list[dict[str, Any]], list[str]]:
    """
    One-shot loader: reads agent.yaml and all tool YAMLs.

    Returns:
        system_prompt  — the agent's system instruction string
        tool_schemas   — list of OpenAI-formatted tool schemas
        tool_names     — list of tool names (used to look up handlers in tools.py)
    """
    agent_config = load_agent_config()
    tool_names = agent_config.get("tools", [])
    tool_schemas = load_tool_schemas(tool_names)
    system_prompt = agent_config.get("system_prompt", "You are a helpful AI assistant.")

    print(f"[config_loader] Loaded agent: {agent_config.get('name', 'Unknown')}")
    print(f"[config_loader] Loaded {len(tool_schemas)} tool schemas from YAML: {[t['function']['name'] for t in tool_schemas]}")

    return system_prompt, tool_schemas, tool_names
