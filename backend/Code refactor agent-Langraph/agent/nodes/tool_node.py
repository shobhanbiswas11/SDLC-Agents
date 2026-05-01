"""
agent/nodes/tool_node.py — LangGraph node: executes tool calls from the LLM.

Special handling:
  - ``ask_user`` → calls LangGraph ``interrupt()``, pausing the graph until
    the human supplies an answer via the /answer endpoint or CLI prompt.

All other tools are looked up in ``tools.TOOL_HANDLERS`` and executed directly.
Navigation events update ``navigated_file`` / ``created_files`` in state for
the frontend to consume.
"""

from __future__ import annotations

import json

from langgraph.types import interrupt

from agent.state import AgentState
from core.logging import get_logger

logger = get_logger(__name__)

_TERMINAL_TOOLS = {"github_put_file", "git_commit_push"}


def _terminal_tool_response(tool_name: str, tool_result: dict) -> str:
    """Build a final user-facing response for terminal tool results."""
    if tool_result.get("status") == "success":
        parts = [tool_result.get("message") or f"{tool_name} completed successfully."]
        if tool_result.get("file_url"):
            parts.append(f"File URL: {tool_result['file_url']}")
        if tool_result.get("commit_sha"):
            parts.append(f"Commit SHA: {tool_result['commit_sha']}")
        if tool_result.get("commit_url"):
            parts.append(f"Commit URL: {tool_result['commit_url']}")
        return "\n".join(parts)

    error = tool_result.get("error") or "Unknown error"
    stderr = tool_result.get("stderr") or ""
    return (
        f"GitHub push failed via `{tool_name}`.\n"
        f"Error: {error}"
        + (f"\nDetails: {stderr}" if stderr else "")
    )


async def tool_node(state: AgentState) -> dict:
    """
    Execute every pending tool call requested by the LLM.

    Returns a partial state update with:
    - ``pending_tool_calls`` cleared
    - ``history`` extended with tool-result messages
    - ``navigated_file`` / ``created_files`` updated when relevant
    """
    # Import here to avoid circular imports at module load time
    from tools import TOOL_HANDLERS

    tool_calls = state.get("pending_tool_calls", [])
    history = list(state.get("history", []))
    workspace_path = state.get("workspace_path", ".")
    navigated_file = state.get("navigated_file", "")
    created_files = list(state.get("created_files", []))
    finalize_after_tool = False
    final_response = state.get("last_response", "")

    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        logger.info("tool_node: executing '%s'", tool_name)

        # ── Parse arguments ────────────────────────────────────────────────────
        try:
            tool_args = json.loads(tool_call["arguments"])
        except json.JSONDecodeError as exc:
            logger.warning("tool_node: invalid JSON args for '%s': %s", tool_name, exc)
            history.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(
                        {
                            "status": "error",
                            "error": (
                                f"Your tool arguments were invalid JSON: {exc}. "
                                f"Raw: {tool_call['arguments'][:200]}... "
                                "Please retry with shorter, valid JSON arguments."
                            ),
                        }
                    ),
                }
            )
            continue

        # ── ask_user → pause the graph ─────────────────────────────────────────
        if tool_name == "ask_user":
            question = tool_args.get("question", "")
            logger.info("tool_node: ask_user interrupt — '%s'", question[:80])
            answer = interrupt(question)  # LangGraph pauses graph execution here ✋
            tool_result = {"status": "success", "answer": answer}

        # ── All other tools ────────────────────────────────────────────────────
        else:
            handler = TOOL_HANDLERS.get(tool_name)
            if handler is None:
                tool_result = {
                    "status": "error",
                    "error": (
                        f"Unknown tool: '{tool_name}'. "
                        f"Available: {list(TOOL_HANDLERS.keys())}"
                    ),
                }
                logger.error("tool_node: unknown tool '%s'", tool_name)
            else:
                try:
                    tool_result = await handler(workspace_path=workspace_path, **tool_args)
                except Exception as exc:
                    tool_result = {
                        "status": "error",
                        "error": f"Tool '{tool_name}' raised: {str(exc)}",
                    }
                    logger.exception("tool_node: '%s' raised an exception", tool_name)

        # ── Track navigation / file-creation events ────────────────────────────
        if tool_name == "navigate_to_file" and tool_result.get("status") == "success":
            nav = tool_result.get("resolved_path") or tool_args.get("file_path", "")
            if nav:
                navigated_file = nav

        elif tool_name == "read_file" and tool_result.get("status") == "success":
            rp = tool_result.get("resolved_path") or tool_args.get("file_path", "")
            if rp:
                navigated_file = rp

        elif tool_name == "write_file" and tool_result.get("status") == "success":
            if tool_result.get("created"):
                fp = tool_result.get("file_path") or tool_args.get("file_path", "")
                if fp and fp not in created_files:
                    created_files.append(fp)
            nav = tool_result.get("file_path") or tool_args.get("file_path", "")
            if nav:
                navigated_file = nav

        # Append result to conversation history
        history.append(
            {
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(tool_result),
            }
        )

        if tool_name in _TERMINAL_TOOLS:
            final_response = _terminal_tool_response(tool_name, tool_result)
            history.append({"role": "assistant", "content": final_response})
            finalize_after_tool = True
            break

    return {
        **state,
        "pending_tool_calls": [],
        "history": history,
        "navigated_file": navigated_file,
        "created_files": created_files,
        "last_response": final_response,
        "finalize_after_tool": finalize_after_tool,
        "status": "idle" if finalize_after_tool else "thinking",
    }
