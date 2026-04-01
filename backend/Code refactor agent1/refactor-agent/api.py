"""
api.py — FastAPI server for the Code Refactoring Agent.

Endpoints:
  GET  /                                   → health check
  GET  /api/agents                         → list available agent
  POST /api/workflows                      → start a new session
  POST /api/workflows/{id}/messages        → send a message
  GET  /api/workflows/{id}/status          → poll for response
  DELETE /api/workflows/{id}               → stop session
"""

import uuid
import os
import subprocess
from datetime import timedelta
from typing import Any, Dict, Optional
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from temporalio.client import Client

from workflow import AgentWorkflow, WorkflowInput

load_dotenv()

app = FastAPI(title="Code Refactoring Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TASK_QUEUE = "refactor-agent-queue"
TEMPORAL_ADDRESS = os.environ.get("TEMPORAL_ADDRESS", "localhost:7233")
TEMPORAL_NAMESPACE = os.environ.get("TEMPORAL_NAMESPACE", "default")
TEMPORAL_API_KEY = os.environ.get("TEMPORAL_API_KEY")
TEMPORAL_TLS = os.environ.get("TEMPORAL_TLS")

_temporal_client: Optional[Client] = None


def _resolve_temporal_tls_setting() -> bool | None:
    if not TEMPORAL_TLS or not TEMPORAL_TLS.strip():
        return None
    value = TEMPORAL_TLS.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return None


async def get_client() -> Client:
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


class StartRequest(BaseModel):
    agent_id: str = "refactoring-agent"
    workspace_path: str = "."
    source_type: str = "local"
    github_url: Optional[str] = None
    github_branch: Optional[str] = None


class MessageRequest(BaseModel):
    message: str


@app.get("/")
async def root():
    return {"status": "ok", "message": "Code Refactoring Agent API running on port 8002"}


@app.get("/api/agents")
async def list_agents() -> Dict[str, Any]:
    return {
        "agents": [{
            "id": "refactoring-agent",
            "name": "Code Refactoring Agent",
            "description": "Analyzes code for code smells and suggests safe refactors.",
            "tools": ["analyze_code", "suggest_refactor", "apply_refactor", "diff_preview", "run_tests", "read_file", "write_file", "list_files", "ask_user"],
        }]
    }


@app.post("/api/workflows")
async def start_workflow(req: StartRequest) -> Dict[str, str]:
    client = await get_client()
    workflow_id = f"refactor-{uuid.uuid4().hex[:8]}"

    source_type = (req.source_type or "local").strip().lower()
    if source_type not in {"local", "github"}:
        raise HTTPException(status_code=400, detail="source_type must be either 'local' or 'github'.")

    resolved_workspace_path = req.workspace_path
    if source_type == "github":
        github_url = (req.github_url or "").strip()
        if not github_url:
            raise HTTPException(status_code=400, detail="github_url is required when source_type is 'github'.")

        clone_root = Path(__file__).resolve().parent / ".refactor_repos"
        clone_root.mkdir(parents=True, exist_ok=True)
        clone_path = clone_root / workflow_id

        clone_cmd = ["git", "clone", "--depth", "1"]
        if req.github_branch and req.github_branch.strip():
            clone_cmd.extend(["--branch", req.github_branch.strip()])
        clone_cmd.extend([github_url, str(clone_path)])

        try:
            subprocess.run(
                clone_cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=500, detail="GitHub clone timed out after 120 seconds.")
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="git is not installed or not available in PATH.")
        except subprocess.CalledProcessError as e:
            error_output = (e.stderr or e.stdout or "Unknown git clone error").strip()
            raise HTTPException(status_code=500, detail=f"Failed to clone GitHub repository: {error_output}")

        resolved_workspace_path = str(clone_path)

    await client.start_workflow(
        AgentWorkflow.run,
        WorkflowInput(agent_id=req.agent_id, workspace_path=resolved_workspace_path),
        id=workflow_id,
        task_queue=TASK_QUEUE,
        execution_timeout=timedelta(hours=24),
    )
    return {
        "workflow_id": workflow_id,
        "source_type": source_type,
        "workspace_path": resolved_workspace_path,
    }


@app.post("/api/workflows/{workflow_id}/messages")
async def send_message(workflow_id: str, req: MessageRequest) -> Dict[str, str]:
    client = await get_client()
    handle = client.get_workflow_handle(workflow_id)
    try:
        await handle.signal(AgentWorkflow.send_message, req.message)
        return {"status": "message_sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflows/{workflow_id}/status")
async def get_status(workflow_id: str) -> Dict[str, Any]:
    client = await get_client()
    handle = client.get_workflow_handle(workflow_id)
    try:
        status = await handle.query(AgentWorkflow.get_status)
        return {"status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/workflows/{workflow_id}")
async def stop_workflow(workflow_id: str) -> Dict[str, str]:
    client = await get_client()
    handle = client.get_workflow_handle(workflow_id)
    try:
        await handle.signal(AgentWorkflow.stop)
        return {"status": "stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8002))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
