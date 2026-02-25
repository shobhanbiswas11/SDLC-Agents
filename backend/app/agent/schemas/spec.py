from pydantic import BaseModel, Field
from typing import List, Optional


class APIEndpoint(BaseModel):
    path: str
    method: str
    response_model: str


class APISpec(BaseModel):
    style: Optional[str] = "rest"
    endpoints: Optional[List[APIEndpoint]] = []


class DBSchema(BaseModel):
    type: Optional[str] = "none"
    orm: Optional[str] = "none"


class CodingStandards(BaseModel):
    style: Optional[str] = "pep8"
    linters: Optional[List[str]] = ["ruff"]
    formatter: Optional[str] = "black"


class Spec(BaseModel):
    version: str = "0.1"
    project_name: Optional[str] = None
    language: Optional[str] = None
    framework: Optional[str] = None
    package_manager: Optional[str] = None
    entry_point: Optional[str] = None
    features: Optional[List[str]] = []
    api: Optional[APISpec] = APISpec()
    db: Optional[DBSchema] = DBSchema()
    coding_standards: Optional[CodingStandards] = CodingStandards()