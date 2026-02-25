from pydantic import BaseModel
from typing import Optional, List, Dict


class GenerateResponse(BaseModel):
    status: str
    run_id: Optional[str] = None
    missing_fields: Optional[List[str]] = None
    questions: Optional[str] = None
    artifact_path: Optional[str] = None
    standards: Optional[Dict] = None