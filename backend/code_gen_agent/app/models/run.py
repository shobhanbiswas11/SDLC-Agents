from pydantic import BaseModel
from typing import Optional


class RunStatus(BaseModel):
    run_id: str
    status: str
    stage: Optional[str] = None
    artifact_path: Optional[str] = None