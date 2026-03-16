from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.agent.schemas.spec import Spec


class GenerateRequest(BaseModel):
    text: Optional[str] = None
    spec: Optional[Spec] = None
    answers: Optional[Dict[str, Any]] = None

    class Config:
        extra = "forbid"  