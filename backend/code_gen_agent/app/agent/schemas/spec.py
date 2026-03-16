from pydantic import BaseModel, Field
from typing import List, Optional


# ----------------------------
# API
# ----------------------------

class APIEndpoint(BaseModel):
    path: str
    method: str
    response_model: Optional[str] = None
    request_model: Optional[str] = None
    auth_required: Optional[bool] = False


class APISpec(BaseModel):
    style: Optional[str] = "rest"
    endpoints: List[APIEndpoint] = Field(default_factory=list)


# ----------------------------
# Database
# ----------------------------

class DBSchema(BaseModel):
    type: Optional[str] = None          # postgres, mysql, sqlite, mongodb
    orm: Optional[str] = None           # sqlalchemy, prisma, mongoose


# ----------------------------
# Authentication
# ----------------------------

class AuthSpec(BaseModel):
    type: Optional[str] = None          # jwt, oauth, session, none
    provider: Optional[str] = None      # google, github, etc


# ----------------------------
# Architecture
# ----------------------------

class ArchitectureSpec(BaseModel):
    style: Optional[str] = None         # mvc, clean, feature-based
    folder_structure_required: Optional[bool] = True


# ----------------------------
# Scope / Generation Rules
# ----------------------------

class ScopeSpec(BaseModel):
    starter_code_only: Optional[bool] = True
    minimal_working: Optional[bool] = True
    advanced_features: Optional[bool] = False
    include_comments: Optional[bool] = True


# ----------------------------
# Other Requirements
# ----------------------------

class RequirementsSpec(BaseModel):
    use_env_variables: Optional[bool] = True
    basic_error_handling: Optional[bool] = True
    restful_api_design: Optional[bool] = True


# ----------------------------
# Coding Standards
# ----------------------------

class CodingStandards(BaseModel):
    style: Optional[str] = "pep8"
    linters: List[str] = Field(default_factory=lambda: ["ruff"])
    formatter: Optional[str] = "black"


# ----------------------------
# Main Spec
# ----------------------------

class Spec(BaseModel):
    version: str = "0.2"

    # Project identity
    project_name: Optional[str] = None
    app_type: Optional[str] = None      # e.g. blog, ecommerce, crm

    # Tech stack
    frontend: Optional[str] = None
    backend: Optional[str] = None
    language: Optional[str] = None
    framework: Optional[str] = None
    package_manager: Optional[str] = None
    entry_point: Optional[str] = None

    # Features
    core_features: List[str] = Field(default_factory=list)

    # Structured configs
    api: APISpec = Field(default_factory=APISpec)
    db: DBSchema = Field(default_factory=DBSchema)
    auth: AuthSpec = Field(default_factory=AuthSpec)
    architecture: ArchitectureSpec = Field(default_factory=ArchitectureSpec)
    scope: ScopeSpec = Field(default_factory=ScopeSpec)
    requirements: RequirementsSpec = Field(default_factory=RequirementsSpec)
    coding_standards: CodingStandards = Field(default_factory=CodingStandards)