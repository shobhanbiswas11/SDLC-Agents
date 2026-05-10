"""
API Routes
-----------
Build orchestration endpoints + natural language chat interface.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from celery.result import AsyncResult

from app.worker.tasks import run_build_task
from app.worker.celery_app import celery_app

from app.db.database import SessionLocal
from app.db.models import Build, Log

from app.services.project_manager import clone_repo, detect_project_type, get_build_config
from app.services.chat_parser import parse_chat_message

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


class BuildRequest(BaseModel):
    github_url: Optional[str] = None
    project_path: Optional[str] = None
    branch: Optional[str] = "main"


@router.post("/build")
def start_build(request: BuildRequest):
    """
    Start a build. Accepts either a GitHub URL or a local project path.
    If a GitHub URL is provided, the repo is cloned first.
    """
    # ─── Validate input ──────────────────────────────────
    if not request.github_url and not request.project_path:
        raise HTTPException(
            status_code=400,
            detail="Either 'github_url' or 'project_path' is required."
        )

    project_path = request.project_path
    github_url = request.github_url

    # ─── Clone if GitHub URL provided ─────────────────────
    if github_url:
        try:
            clone_result = clone_repo(github_url, request.branch or "main")
            project_path = clone_result["project_path"]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # ─── Detect project type ──────────────────────────────
    project_type = detect_project_type(project_path)

    if not project_type:
        raise HTTPException(
            status_code=400,
            detail=f"Could not detect project type in: {project_path}. "
                   f"Supported: Node.js (package.json), Python (requirements.txt), Go (go.mod), Java (pom.xml/build.gradle)"
        )

    build_config = get_build_config(project_type)

    # ─── Dispatch Celery task ─────────────────────────────
    task = run_build_task.delay(
        project_path,
        project_type,
        build_config,
        github_url,
    )

    return {
        "task_id": task.id,
        "status": "STARTED",
        "project_type": build_config["label"],
        "project_path": project_path,
        "github_url": github_url,
    }


@router.post("/chat")
def chat(request: ChatRequest):
    """
    Natural language chat endpoint.
    Parses user message, extracts intent, and either triggers a build
    or returns a conversational reply.
    """
    intent = parse_chat_message(request.message)

    # ── Help / General: just reply ────────────────────
    if intent.intent in ("help", "general"):
        return {
            "intent": intent.intent,
            "reply": intent.reply,
        }

    # ── Status: look up latest build ──────────────────
    if intent.intent == "status":
        db = SessionLocal()
        latest = db.query(Build).order_by(Build.created_at.desc()).first()
        db.close()

        if not latest:
            return {
                "intent": "status",
                "reply": "You haven't run any builds yet. Paste a GitHub URL or local path to get started!",
            }

        return {
            "intent": "status",
            "reply": (
                f"Your latest build (`{latest.id[:8]}...`) is **{latest.status}**.\n\n"
                f"- **Project:** {latest.github_url or latest.project_path}\n"
                f"- **Type:** {latest.project_type}\n"
                f"- **Started:** {latest.created_at}"
            ),
            "build_id": latest.id,
            "build_status": latest.status,
        }

    # ── Build: trigger the pipeline ───────────────────
    if intent.intent == "build":
        project_path = intent.project_path
        github_url = intent.github_url

        if github_url:
            try:
                clone_result = clone_repo(github_url, intent.branch)
                project_path = clone_result["project_path"]
            except ValueError as e:
                return {
                    "intent": "build",
                    "reply": f"I couldn't clone that repository: {e}",
                    "error": True,
                }

        project_type = detect_project_type(project_path)

        if not project_type:
            return {
                "intent": "build",
                "reply": (
                    f"I couldn't detect the project type at `{project_path}`. "
                    "I support Node.js, Python, Go, and Java projects."
                ),
                "error": True,
            }

        build_config = get_build_config(project_type)

        task = run_build_task.delay(
            project_path,
            project_type,
            build_config,
            github_url,
        )

        return {
            "intent": "build",
            "reply": intent.reply,
            "task_id": task.id,
            "project_type": build_config["label"],
            "project_path": project_path,
            "github_url": github_url,
        }

    return {"intent": "unknown", "reply": intent.reply}


@router.get("/status/{task_id}")
def get_status(task_id: str):
    task = AsyncResult(task_id, app=celery_app)

    response = {
        "task_id": task_id,
        "status": task.status
    }

    if task.status == "SUCCESS":
        response["result"] = task.result

    elif task.status == "FAILURE":
        response["error"] = str(task.result)

    return response


@router.get("/builds")
def get_builds():
    db = SessionLocal()
    builds = db.query(Build).order_by(Build.created_at.desc()).limit(50).all()
    db.close()

    return [
        {
            "id": b.id,
            "project_path": b.project_path,
            "github_url": b.github_url,
            "project_type": b.project_type,
            "status": b.status,
            "created_at": str(b.created_at) if b.created_at else None,
            "completed_at": str(b.completed_at) if b.completed_at else None,
        }
        for b in builds
    ]


@router.get("/logs/{build_id}")
def get_logs(build_id: str):
    db = SessionLocal()
    logs = db.query(Log).filter(Log.build_id == build_id).all()
    db.close()

    return [
        {
            "id": l.id,
            "build_id": l.build_id,
            "message": l.message,
            "timestamp": str(l.timestamp) if l.timestamp else None,
        }
        for l in logs
    ]