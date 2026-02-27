from pydantic import BaseModel
from typing import Optional, Dict, List, Any


class GenerateResponse(BaseModel):
    status: str
    missing_fields: Optional[List[str]] = None
    questions: Optional[Any] = None
    spec: Optional[dict] = None

    tree: Optional[List[str]] = None
    files: Optional[Dict[str, str]] = None
    init_instructions: Optional[str] = None