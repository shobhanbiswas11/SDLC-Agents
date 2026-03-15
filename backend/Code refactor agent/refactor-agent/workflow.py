"""
workflow.py — The Temporal Workflow for the Code Refactoring Agent.

ReAct loop: think → act → observe → repeat until the LLM gives a final answer.
Includes a confirmation gate — apply_refactor requires user approval first.
"""

import asyncio
import json
import re
from urllib.parse import unquote
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.exceptions import TimeoutError as TemporalTimeoutError

from config_loader import load_all_config

SYSTEM_PROMPT, TOOL_SCHEMAS, TOOL_NAMES = load_all_config()


def _augment_message_with_github_paths(message: str) -> str:
    """
    If user provides a GitHub blob URL, append a normalized repository-relative
    file path hint so the agent can call file tools correctly.
    """
    pattern = re.compile(r"https?://github\.com/[^/\s]+/[^/\s]+/blob/[^/\s]+/(?P<path>[^\s?#]+)")
    matches = list(pattern.finditer(message))
    if not matches:
        return message

    extracted_paths: list[str] = []
    for match in matches:
        path = unquote(match.group("path")).strip().lstrip("/")
        if path and path not in extracted_paths:
            extracted_paths.append(path)

    if not extracted_paths:
        return message

    hint_lines = ["", "Detected GitHub blob URL(s). Use these repository-relative file path(s):"]
    hint_lines.extend([f"- {path}" for path in extracted_paths])
    return message + "\n" + "\n".join(hint_lines)


@dataclass
class WorkflowInput:
    """Data passed when starting a new workflow session."""
    agent_id: str = "refactoring-agent"
    workspace_path: str = "."
    query: str = ""


@workflow.defn
class AgentWorkflow:
    """The main refactoring agent workflow. Temporal keeps this alive in memory."""

    def __init__(self):
        self._history: list[dict] = []
        self._pending_messages: list[str] = []
        self._last_response: str = ""
        self._status: str = "idle"
        self._waiting_for_user: bool = False
        self._user_answer: str = ""
        self._workspace_path: str = "."
        self._should_exit: bool = False

    # ── Signals (push data in) ────────────────────────────────────────────

    @workflow.signal
    async def send_message(self, message: str) -> None:
        """Frontend sends a user message or an answer to ask_user."""
        if self._waiting_for_user:
            self._user_answer = message
            self._waiting_for_user = False
        else:
            self._last_response = ""
            self._pending_messages.append(message)

    @workflow.signal
    async def stop(self) -> None:
        self._should_exit = True

    # ── Queries (read data out) ───────────────────────────────────────────



    @workflow.query
    def get_status(self) -> dict:
        return {
            "status": self._status,
            "last_response": self._last_response,
            "waiting_for_user": self._waiting_for_user,
            "message_count": len(self._history),
        }

    # ── Main Loop ─────────────────────────────────────────────────────────

    @workflow.run
    async def run(self, input: WorkflowInput | dict) -> dict[str, Any]:
        if isinstance(input, dict):
            self._workspace_path = input.get("workspace_path", ".")
            initial_query = input.get("query", "")
        else:
            self._workspace_path = input.workspace_path
            initial_query = input.query

        if initial_query:
            self._pending_messages.append(initial_query)

        self._history = [{"role": "system", "content": SYSTEM_PROMPT}]

        while not self._should_exit:
            try:
                await workflow.wait_condition(
                    lambda: len(self._pending_messages) > 0 or self._should_exit,
                    timeout=timedelta(hours=1),
                )
            except TemporalTimeoutError:
                break

            if self._should_exit:
                break

            if self._pending_messages:
                message = self._pending_messages.pop(0)
                self._status = "thinking"
                self._last_response = ""
                response = await self._process_message(message)
                self._last_response = response
                self._status = "idle"

        return {"status": "stopped"}

    # ── ReAct Loop ────────────────────────────────────────────────────────

    async def _process_message(self, user_message: str) -> str:
        """
        The core think → act → observe loop.
        Includes a confirmation gate for apply_refactor.
        """
        normalized_message = _augment_message_with_github_paths(user_message)
        self._history.append({"role": "user", "content": normalized_message})

        max_steps = 15  # More steps for multi-tool refactoring workflows

        for _ in range(max_steps):
            # Step 1: Ask the LLM
            llm_response = await workflow.execute_activity(
                "llm_call",
                args=[self._history, TOOL_SCHEMAS],
                start_to_close_timeout=timedelta(seconds=120),
            )

            # Step 2: Final text answer?
            tool_calls = llm_response.get("tool_calls")
            text_response = llm_response.get("content", "")
            print(f"[AgentWorkflow] LLM response: {text_response[:200]}... Tool calls: {tool_calls}")
            if not tool_calls:
                self._history.append({"role": "assistant", "content": text_response})
                return text_response or "I'm not sure how to help with that."

            # Step 3: Log tool request
            self._history.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": tc["id"], "type": "function",
                     "function": {"name": tc["name"], "arguments": tc["arguments"]}}
                    for tc in tool_calls
                ]
            })

            # Step 4: Execute each tool
            for tool_call in tool_calls:
                tool_name = tool_call["name"]

                # Parse arguments — LLM sometimes returns truncated/invalid JSON
                try:
                    tool_args = json.loads(tool_call["arguments"])
                except json.JSONDecodeError as e:
                    # Tell the LLM its JSON was bad so it can retry properly
                    self._history.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps({
                            "status": "error",
                            "error": f"Your tool arguments were invalid JSON: {e}. "
                                     f"Raw: {tool_call['arguments'][:200]}... "
                                     "Please retry with shorter, valid JSON arguments."
                        }),
                    })
                    continue

                # Special handling: ask_user pauses for human input
                if tool_name == "ask_user":
                    question = tool_args.get("question", "")
                    self._status = "waiting_for_user"
                    self._waiting_for_user = True
                    self._last_response = f"❓ {question}"

                    await workflow.wait_condition(
                        lambda: not self._waiting_for_user,
                        timeout=timedelta(hours=1),
                    )
                    self._status = "thinking"
                    tool_result = {"status": "success", "answer": self._user_answer}
                else:
                    # Run tool as Temporal Activity
                    tool_result = await workflow.execute_activity(
                        "run_tool",
                        args=[tool_name, tool_args, self._workspace_path],
                        start_to_close_timeout=timedelta(seconds=120),
                    )

                # Add result to history
                self._history.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(tool_result),
                })
                #print the entire hitory after each tool call for better visibility into the agent's thought process
                print(
                    json.dumps(
                        self._history,
                        indent=2,
                        ensure_ascii=False,
                    )
                )

        return "I was unable to complete the task within the allowed steps."
