"""
workflow.py — The "brain" of the agent.

This is a Temporal Workflow — think of it as a long-running conversation session
that survives restarts, crashes, and network hiccups.

How it works:
  1. The workflow starts and waits for the user to send a message (a Temporal Signal).
  2. When a message arrives, it runs the ReAct loop:
       a. Send conversation history + tool schemas to Azure OpenAI.
       b. If the AI replies with normal text → done, return the text.
       c. If the AI replies with a tool call → run the tool, add result to history, go to (a).
  3. Stores the final reply so the API can read it.
  4. Waits for the next message and repeats forever.
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.exceptions import TimeoutError as TemporalTimeoutError

# Import tool schemas from YAML files instead of hardcoding them inline.
# config_loader.py reads config/agent.yaml and config/tools/*.yaml
# and converts them into OpenAI-compatible schema dicts.
from config_loader import load_all_config

# Load everything once at module startup:
#   SYSTEM_PROMPT — the agent's personality and instructions (from config/agent.yaml)
#   TOOL_SCHEMAS  — list of OpenAI function schemas (from config/tools/*.yaml)
#   TOOL_NAMES    — list of tool names (used to verify handlers exist)
SYSTEM_PROMPT, TOOL_SCHEMAS, TOOL_NAMES = load_all_config()

# ──────────────────────────────────────────────
# DATA STRUCTURES
# ──────────────────────────────────────────────

@dataclass
class WorkflowInput:
    """Data passed when starting a new workflow session."""
    agent_id: str = "reviewer"
    workspace_path: str = "."
    query: str = ""  # Optional first message


@workflow.defn
class AgentWorkflow:
    """
    The main agent workflow class.
    Temporal keeps this alive in memory and persists its state automatically.
    """

    def __init__(self):
        # Stores all messages exchanged (system + user + assistant + tools)
        self._history: list[dict] = []
        # Messages the user has sent but not yet processed
        self._pending_messages: list[str] = []
        # The last reply from the agent (what the frontend polls for)
        self._last_response: str = ""
        # Current status shown to the frontend
        self._status: str = "idle"
        # Set to True when paused waiting for the user to answer ask_user
        self._waiting_for_user: bool = False
        # User's answer to an ask_user call
        self._user_answer: str = ""
        # Path to the workspace directory
        self._workspace_path: str = "."
        self._should_exit: bool = False

    # ── Temporal Signals (push data INTO the workflow) ──────────────────────

    @workflow.signal
    async def send_message(self, message: str) -> None:
        """Frontend calls this to send a user message."""
        if self._waiting_for_user:
            # The agent previously asked the user a question — this is the answer
            self._user_answer = message
            self._waiting_for_user = False
        else:
            self._last_response = ""
            self._pending_messages.append(message)

    @workflow.signal
    async def stop(self) -> None:
        """Stop the workflow."""
        self._should_exit = True

    # ── Temporal Queries (read data OUT of the workflow) ─────────────────────

    @workflow.query
    def get_status(self) -> dict:
        """Frontend polls this to check if the agent has finished thinking."""
        return {
            "status": self._status,
            "last_response": self._last_response,
            "waiting_for_user": self._waiting_for_user,
            "pending_question": "",  # Could be extended to return ask_user question
            "message_count": len(self._history)
        }

    # ── Main Execution Loop ───────────────────────────────────────────────────

    @workflow.run
    async def run(self, input: WorkflowInput | dict) -> dict[str, Any]:
        """
        The entry point for the workflow.
        Runs forever, waiting for messages, processing them, and waiting again.
        """
        # Handle both dict and dataclass inputs (Temporal serializes to dict)
        if isinstance(input, dict):
            self._workspace_path = input.get("workspace_path", ".")
            initial_query = input.get("query", "")
        else:
            self._workspace_path = input.workspace_path
            initial_query = input.query

        # If there was an initial query, queue it up
        if initial_query:
            self._pending_messages.append(initial_query)

        # Initialize conversation with the agent's personality
        self._history = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Idle forever until stopped (or 1-hour timeout with no activity)
        idle_timeout = timedelta(hours=1)

        while not self._should_exit:
            try:
                # Sleep until a new message arrives (or we time out)
                await workflow.wait_condition(
                    lambda: len(self._pending_messages) > 0 or self._should_exit,
                    timeout=idle_timeout,
                )
            except TemporalTimeoutError:
                # No messages for 1 hour — shut down quietly
                break

            if self._should_exit:
                break

            # Process the next queued message
            if self._pending_messages:
                message = self._pending_messages.pop(0)
                self._status = "thinking"
                self._last_response = ""
                response = await self._process_message(message)
                self._last_response = response
                self._status = "idle"

        return {"status": "stopped"}

    # ── The ReAct Agent Loop ──────────────────────────────────────────────────

    async def _process_message(self, user_message: str) -> str:
        """
        The core "think → act → observe" loop.

        1. Adds user message to history.
        2. Asks the LLM what to do next.
        3. If the LLM wants to call a tool, runs the tool and feeds the result back.
        4. Repeats until the LLM gives a final text reply.
        """
        # Add the user's message to the conversation
        self._history.append({"role": "user", "content": user_message})

        max_steps = 10  # Prevent infinite loops

        for _ in range(max_steps):
            # ── Step 1: Ask the LLM ──────────────────────────────────────────
            # We run the LLM call as a Temporal Activity (outside the workflow sandbox)
            # so that network calls are allowed and retried automatically on failure.
            llm_response = await workflow.execute_activity(
                "llm_call",
                args=[self._history, TOOL_SCHEMAS],
                start_to_close_timeout=timedelta(seconds=120),
            )

            # ── Step 2: Did the LLM give a final answer? ─────────────────────
            tool_calls = llm_response.get("tool_calls")
            text_response = llm_response.get("content", "")

            if not tool_calls:
                # No tool calls → the LLM gave us a final text answer
                self._history.append({"role": "assistant", "content": text_response})
                return text_response or "I'm not sure how to help with that."

            # ── Step 3: Log the AI's tool request in history ─────────────────
            self._history.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": tc["id"], "type": "function",
                     "function": {"name": tc["name"], "arguments": tc["arguments"]}}
                    for tc in tool_calls
                ]
            })

            # ── Step 4: Execute each tool the AI requested ───────────────────
            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_args = json.loads(tool_call["arguments"])

                # Special case: ask_user pauses the workflow until the human answers
                if tool_name == "ask_user":
                    question = tool_args.get("question", "")
                    self._status = "waiting_for_user"
                    self._waiting_for_user = True
                    self._last_response = f"❓ {question}"

                    # Pause until the user sends an answer via the send_message signal
                    await workflow.wait_condition(
                        lambda: not self._waiting_for_user,
                        timeout=timedelta(hours=1)
                    )
                    self._status = "thinking"
                    tool_result = {"status": "success", "answer": self._user_answer}
                else:
                    # Run the tool as a Temporal Activity (safe, retried, timed out)
                    tool_result = await workflow.execute_activity(
                        "run_tool",
                        args=[tool_name, tool_args, self._workspace_path],
                        start_to_close_timeout=timedelta(seconds=300),  # 5 min for slow tools
                    )

                # Add the tool result to history so the LLM can read it
                self._history.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(tool_result)
                })

        return "I was unable to complete the task within the allowed steps."
