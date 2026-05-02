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
import concurrent.futures
from dotenv import load_dotenv
from temporalio.client import Client
from temporalio.worker import Worker

# Import our workflow and activities
from workflow import AgentWorkflow
from activities import llm_call, run_tool, gather_context

# Load .env file for Temporal Cloud settings
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
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
    print("Starting Simple Agent Worker...")
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

    # We need a thread pool executor because some of our activities (llm_call, gather_context) are synchronous
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as activity_executor:
        # Start the worker — it will run until you press Ctrl+C
        async with Worker(
            client,
            task_queue=TASK_QUEUE,
            workflows=[AgentWorkflow],       # Register our workflow class
            activities=[llm_call, run_tool, gather_context],  # Register our activity functions
            activity_executor=activity_executor, # Provide thread pool to run synchronous activities
            max_concurrent_activities=int(os.environ.get("TEMPORAL_MAX_ACTIVITIES", 101)),
            max_concurrent_workflow_tasks=int(os.environ.get("TEMPORAL_MAX_WORKFLOW_TASKS", 100)),
        ):
            print("✅ Worker is running. Press Ctrl+C to stop.\n")
            await asyncio.Event().wait()  # Block forever


if __name__ == "__main__":
    asyncio.run(main())