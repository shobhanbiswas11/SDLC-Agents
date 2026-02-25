from pydantic import BaseModel
from typing import Optional
from app.agent.schemas.spec import Spec


class GenerateRequest(BaseModel):
    """
    Request model for project generation.

    Either:
    - text: free-form requirement string
    OR
    - spec: structured specification JSON
    """

    text: Optional[str] = None
    spec: Optional[Spec] = None

    class Config:
        extra = "forbid"  # Prevent unknown fields