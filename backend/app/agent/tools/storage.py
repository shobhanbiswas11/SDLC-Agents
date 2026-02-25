import os
from app.core.config import settings


def save_artifact(path: str) -> str:
    os.makedirs(settings.ARTIFACT_DIR, exist_ok=True)
    return path  # Later replace with Azure Blob upload