"""
agent/nodes/llm_node.py — LangGraph node: calls Azure OpenAI and decides next action.

The node reads the trimmed conversation history, sends it to the LLM with all
available tool schemas, and returns updated state with either:
  - ``pending_tool_calls`` populated  → the tool_node will execute them next
  - ``last_response`` set             → the agent has produced a final answer
"""

from __future__ import annotations

import os

from agent.state import AgentState
from agent.utils.history import trim_history
from agent.utils.openai_client import get_openai_client
from core.config_loader import load_all_config
from core.logging import get_logger

logger = get_logger(__name__)

# Load tool schemas once at module import time
_SYSTEM_PROMPT, TOOL_SCHEMAS, _TOOL_NAMES = load_all_config()


async def llm_node(state: AgentState) -> dict:
    """
    Call Azure OpenAI with the current conversation history and tool schemas.

    Returns a partial state update containing either pending tool calls
    (agent wants to act) or a final text response (agent is done).
    """
    client = get_openai_client()
    deployment = (
        os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT")
        or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    )

    history = state.get("history", [])
    trimmed = trim_history(history)

    logger.debug("llm_node: sending %d messages to %s", len(trimmed), deployment)

    try:
        response = await client.chat.completions.create(
            model=deployment,
            messages=trimmed,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0.2,
            max_completion_tokens=4096,
            timeout=60,
        )
    except Exception as exc:
        error_msg = f"⚠️ LLM call failed: {type(exc).__name__}: {str(exc)[:200]}"
        logger.error("llm_node error: %s", error_msg)
        return {
            **state,
            "last_response": error_msg,
            "pending_tool_calls": [],
            "status": "idle",
            "history": history + [{"role": "assistant", "content": error_msg}],
        }

    message = response.choices[0].message

    # ── Agent wants to call tools ──────────────────────────────────────────────
    if message.tool_calls:
        tool_calls_data = [
            {
                "id": tc.id,
                "name": tc.function.name,
                "arguments": tc.function.arguments,
            }
            for tc in message.tool_calls
        ]
        logger.info(
            "llm_node: tool calls requested → %s",
            [tc["name"] for tc in tool_calls_data],
        )

        updated_history = history + [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"],
                        },
                    }
                    for tc in tool_calls_data
                ],
            }
        ]

        return {
            **state,
            "pending_tool_calls": tool_calls_data,
            "history": updated_history,
            "status": "thinking",
        }

    # ── Agent produced a final text answer ────────────────────────────────────
    text = message.content or ""
    logger.info("llm_node: final response (%d chars)", len(text))
    return {
        **state,
        "pending_tool_calls": [],
        "last_response": text,
        "status": "idle",
        "history": history + [{"role": "assistant", "content": text}],
    }
