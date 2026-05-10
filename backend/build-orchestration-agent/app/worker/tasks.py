"""
Celery Worker Tasks
--------------------
Async task execution for build orchestration.
Supports multiple project types with HITL approval flow.
"""

from app.worker.celery_app import celery_app

from app.executor.podman_runner import PodmanExecutor
from app.analyzer.log_parser import LogAnalyzer
from app.reasoner.azure_llm import AzureReasoner
from app.controller.agent_loop import BuildAgent
from app.services.project_manager import cleanup
from app.memory.vector_store import VectorStore
from app.memory.retriever import Retriever

from datetime import datetime
from app.db.database import SessionLocal
from app.db.models import Build


# -----------------------------------------
# Celery task
# -----------------------------------------
@celery_app.task(name="run_build_task", bind=True)
def run_build_task(self, project_path: str, project_type: str, build_config: dict, github_url: str = None):
    """
    Main build task.
    Initializes the correct executor based on project type,
    runs the agent loop with HITL + RAG, and persists results.
    """
    db = SessionLocal()
    build_id = self.request.id

    # Create build record
    build = Build(
        id=build_id,
        project_path=project_path,
        github_url=github_url,
        project_type=project_type,
        status="RUNNING",
    )
    db.add(build)
    db.commit()

    try:
        # Initialize components with project-specific configuration
        executor = PodmanExecutor(
            image=build_config.get("image", "node:18"),
            build_command=build_config.get("build_command", "npm run build"),
            install_command=build_config.get("install_command", "npm install"),
        )
        analyzer = LogAnalyzer()
        reasoner = AzureReasoner()

        # Initialize RAG retriever (persisted to disk)
        try:
            vector_store = VectorStore(dim=1536)
            retriever = Retriever(vector_store, embedder=reasoner.embed)
            print(f"[RAG] Loaded vector store with {vector_store.size} entries")
        except Exception as e:
            print(f"[RAG] Failed to initialize retriever: {e}")
            retriever = None

        agent = BuildAgent(
            executor, analyzer, reasoner,
            project_type=project_type,
            retriever=retriever,
        )
        agent.task_id = build_id

        result = agent.run(project_path)

        # Update status
        build.status = result.get("status", "UNKNOWN")
        build.completed_at = datetime.utcnow()
        db.commit()

        return result

    except Exception as e:
        build.status = "FAILED"
        build.completed_at = datetime.utcnow()
        db.commit()

        return {"status": "FAILED", "error": str(e)}

    finally:
        db.close()

        # Cleanup cloned repos (only temp workspaces)
        if github_url and project_path:
            try:
                cleanup(project_path)
            except Exception:
                pass