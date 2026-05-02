"""
worker.py — Boots the Temporal Worker for the Code Refactoring Agent.
 
Registers the workflow and activities, then listens on the task queue.
"""
 
import asyncio
import os
from dotenv import load_dotenv
from temporalio.client import Client
from temporalio.worker import Worker
 
from workflow import AgentWorkflow
from activities import llm_call, run_tool
 
load_dotenv()
 
TASK_QUEUE = "refactor-agent-queue"
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
    print("🚀 Starting Code Refactoring Agent Worker...")
    print(f"   Task Queue: {TASK_QUEUE}")
    print(f"   Tools: analyze_code, suggest_refactor, apply_refactor, diff_preview, run_tests, read_file, write_file, list_files, ask_user, git_commit_push")
    print()
 
    connect_kwargs = {
        "namespace": TEMPORAL_NAMESPACE,
        "tls": _resolve_temporal_tls_setting(),
    }
    if TEMPORAL_API_KEY and TEMPORAL_API_KEY.strip():
        connect_kwargs["api_key"] = TEMPORAL_API_KEY.strip()
 
    client = await Client.connect(TEMPORAL_ADDRESS, **connect_kwargs)
 
    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[AgentWorkflow],
        activities=[llm_call, run_tool],
    ):
        print("✅ Worker is running. Press Ctrl+C to stop .\n")
        await asyncio.Event().wait()
 
 
if __name__ == "__main__":
    asyncio.run(main())