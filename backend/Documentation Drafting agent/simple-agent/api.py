"""
api.py — FastAPI server.

Exposes the same HTTP endpoints the frontend (docu-agent-ui) already calls.
All it does is translate HTTP requests into Temporal signals/queries.

Endpoints:
  GET  /api/agents                         → returns the one available agent
  POST /api/workflows                      → starts a new agent session
  POST /api/workflows/{id}/messages        → sends a user message to the session
  GET  /api/workflows/{id}/status          → polls the agent's current response
  DELETE /api/workflows/{id}               → ends the session
"""

import uuid
import os
from datetime import timedelta
from typing import Any, Dict, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from temporalio.client import Client

from workflow import AgentWorkflow, WorkflowInput

# Load .env file so env variables are available
load_dotenv()

app = FastAPI(title="Simple Agent API")

# Allow the React frontend to talk to us (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TASK_QUEUE = "simple-agent-queue"
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

# --- Single global Temporal client (reused across requests) ---
_temporal_client: Optional[Client] = None

async def get_client() -> Client:
    """Connect to the Temporal server (reuse existing connection if available)."""
    global _temporal_client
    if not _temporal_client:
        try:
            connect_kwargs: Dict[str, Any] = {
                "namespace": TEMPORAL_NAMESPACE,
                "tls": _resolve_temporal_tls_setting(),
            }
            if TEMPORAL_API_KEY and TEMPORAL_API_KEY.strip():
                connect_kwargs["api_key"] = TEMPORAL_API_KEY.strip()
            _temporal_client = await Client.connect(TEMPORAL_ADDRESS, **connect_kwargs)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Cannot connect to Temporal: {e}")
    return _temporal_client


# --- Request body models ---
class StartRequest(BaseModel):
    agent_id: str = "reviewer"
    workspace_path: str = "."

class MessageRequest(BaseModel):
    message: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "ok", "message": "Simple Agent API is running on port 8001"}


@app.get("/api/agents")
async def list_agents() -> Dict[str, Any]:
    """
    Returns the single available agent.
    The frontend uses this to populate the agent dropdown.
    """
    return {
        "agents": [{
            "id": "reviewer",
            "name": "Universal Agent",
            "description": "Handles code review, GitHub file operations, documentation, and local file tasks.",
            "tools": ["github_tool", "read_file", "write_file", "list_files", "ask_user"]
        }]
    }


@app.post("/api/workflows")
async def start_workflow(req: StartRequest) -> Dict[str, str]:
    """
    Start a new agent session.
    Creates a new Temporal Workflow with a unique ID and returns that ID.
    The frontend stores this ID and uses it for all future messages.
    """
    client = await get_client()
    workflow_id = f"agent-{uuid.uuid4().hex[:8]}"

    await client.start_workflow(
        AgentWorkflow.run,
        WorkflowInput(agent_id=req.agent_id, workspace_path=req.workspace_path),
        id=workflow_id,
        task_queue=TASK_QUEUE,
        execution_timeout=timedelta(hours=24),
    )

    return {"workflow_id": workflow_id}


@app.post("/api/workflows/{workflow_id}/messages")
async def send_message(workflow_id: str, req: MessageRequest) -> Dict[str, str]:
    """
    Send a user message to the running workflow.
    Uses a Temporal Signal — it's queued and delivered reliably.
    """
    client = await get_client()
    handle = client.get_workflow_handle(workflow_id)
    try:
        await handle.signal(AgentWorkflow.send_message, req.message)
        return {"status": "message_sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflows/{workflow_id}/status")
async def get_status(workflow_id: str) -> Dict[str, Any]:
    """
    Poll the workflow for its current status and latest response.
    The frontend calls this repeatedly after sending a message until `status == 'idle'`.
    """
    client = await get_client()
    handle = client.get_workflow_handle(workflow_id)
    try:
        status = await handle.query(AgentWorkflow.get_status)
        return {"status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/workflows/{workflow_id}")
async def stop_workflow(workflow_id: str) -> Dict[str, str]:
    """Stop and clean up a workflow session."""
    client = await get_client()
    handle = client.get_workflow_handle(workflow_id)
    try:
        await handle.signal(AgentWorkflow.stop)
        return {"status": "stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
