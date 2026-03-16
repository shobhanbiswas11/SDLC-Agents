"""
worker.py — Boots the Temporal Worker.

A Temporal Worker is just a process that:
  1. Connects to the Temporal server.
  2. Registers our Workflow and Activities so Temporal knows where to find them.
  3. Listens on a task queue and runs jobs when Temporal assigns them.

That's all this file does. Nothing complex.
"""

import asyncio
import os
from dotenv import load_dotenv
from temporalio.client import Client
from temporalio.worker import Worker

# Import our workflow and activities
from workflow import AgentWorkflow
from activities import llm_call, run_tool

# Load .env file
load_dotenv()

TASK_QUEUE = "simple-agent-queue"  # Must match the name in api.py
TEMPORAL_ADDRESS = os.environ.get("TEMPORAL_ADDRESS", "localhost:7233")
TEMPORAL_NAMESPACE = os.environ.get("TEMPORAL_NAMESPACE", "default")
TEMPORAL_API_KEY = os.environ.get("TEMPORAL_API_KEY")
TEMPORAL_TLS = os.environ.get("TEMPORAL_TLS")


def _resolve_temporal_tls_setting() -> bool | None:
    if not TEMPORAL_TLS or not TEMPORAL_TLS.strip():
        return None
    value = TEMPORAL_TLS.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return None


async def main():
    print("🚀 Starting Simple Agent Worker...")
    print(f"   Task Queue: {TASK_QUEUE}")
    print(f"   Tools: github_tool, read_file, write_file, list_files, ask_user")
    print()

    # Connect to the Temporal server
    connect_kwargs = {
        "namespace": TEMPORAL_NAMESPACE,
        "tls": _resolve_temporal_tls_setting(),
    }
    if TEMPORAL_API_KEY and TEMPORAL_API_KEY.strip():
        connect_kwargs["api_key"] = TEMPORAL_API_KEY.strip()
    client = await Client.connect(TEMPORAL_ADDRESS, **connect_kwargs)

    # Start the worker — it will run until you press Ctrl+C
    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[AgentWorkflow],       # Register our workflow class
        activities=[llm_call, run_tool],  # Register our activity functions
    ):
        print("✅ Worker is running. Press Ctrl+C to stop.\n")
        await asyncio.Event().wait()  # Block forever


if __name__ == "__main__":
    asyncio.run(main())
