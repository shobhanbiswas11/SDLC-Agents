import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.core.config import settings

router = APIRouter()


@router.get("/{run_id}")
async def download_artifact(run_id: str):
    """Download the generated project ZIP by run_id."""
    # Basic validation — run_id should look like a UUID
    if len(run_id) < 30 or "/" in run_id or "\\" in run_id or ".." in run_id:
        raise HTTPException(status_code=400, detail="Invalid run_id format.")

    zip_path = os.path.join(settings.ARTIFACT_DIR, f"{run_id}.zip")

    if not os.path.isfile(zip_path):
        raise HTTPException(status_code=404, detail="Artifact not found.")

    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=f"project-{run_id[:8]}.zip",
    )
