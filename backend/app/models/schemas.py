from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class UsersAndScale(BaseModel):
    expected_users: Optional[str] = None
    peak_requests: Optional[str] = None
    data_growth: Optional[str] = None


class NFRs(BaseModel):
    availability: Optional[str] = None
    latency: Optional[str] = None
    scalability: Optional[str] = None
    security: List[str] = Field(default_factory=list)
    compliance: List[str] = Field(default_factory=list)


class Constraints(BaseModel):
    timeline: Optional[str] = None
    budget: Optional[Literal["low", "medium", "high"] ] = None
    team_size: Optional[int] = None
    team_skills: List[str] = Field(default_factory=list)


class Preferences(BaseModel):
    cloud: Optional[str] = None  # azure/aws/gcp/agnostic
    deployment: Optional[str] = None  # containers/serverless/vm/unknown
    database: Optional[str] = None


class ChangeEntry(BaseModel):
    version: int
    timestamp: Optional[datetime] = None
    user_message: str
    summary: str
    fields_changed: List[str] = Field(default_factory=list)


class RequirementsMeta(BaseModel):
    version: int = 0
    last_updated: Optional[datetime] = None
    change_log: List[ChangeEntry] = Field(default_factory=list)


class Requirements(BaseModel):
    app_name: Optional[str] = None
    domain: Optional[str] = None
    core_features: List[str] = Field(default_factory=list)
    integrations: List[str] = Field(default_factory=list)

    users_and_scale: UsersAndScale = Field(default_factory=UsersAndScale)
    nfrs: NFRs = Field(default_factory=NFRs)
    constraints: Constraints = Field(default_factory=Constraints)
    preferences: Preferences = Field(default_factory=Preferences)

    constraints_notes: List[str] = Field(default_factory=list)
    meta: RequirementsMeta = Field(default_factory=RequirementsMeta)


class ClarifyingQuestion(BaseModel):
    key: str
    question: str
    reason: str
    options: List[str] = Field(default_factory=list)  # quick-reply suggestions


class IntakeDecision(BaseModel):
    status: Literal["need_more_info", "ready"]
    extracted: Requirements

    missing_critical: List[str] = Field(default_factory=list)
    questions: List[ClarifyingQuestion] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)

    # Optional enhancements for better delta/UX
    change_summary: Optional[str] = None
    fields_changed: List[str] = Field(default_factory=list)  # dot-paths e.g. "nfrs.compliance"


class ImpactAnalysis(BaseModel):
    impact: Literal["none", "low", "medium", "high"]
    reasons: List[str] = Field(default_factory=list)
    should_patch: bool = False
    should_regenerate: bool = False
    suggested_followups: List[str] = Field(default_factory=list)


class ArchitectureOption(BaseModel):
    name: str
    summary: str
    components: List[str]
    when_to_choose: List[str]
    when_not_to_choose: List[str]


class DeltaView(BaseModel):
    version_from: int
    version_to: int

    what_changed: List[str] = Field(default_factory=list)
    new_components_added: List[str] = Field(default_factory=list)
    components_removed: List[str] = Field(default_factory=list)
    unchanged_components: List[str] = Field(default_factory=list)

    decisions_changed: List[str] = Field(default_factory=list)
    diagram_changes: List[str] = Field(default_factory=list)

    migration_steps: List[str] = Field(default_factory=list)
    risk_notes: List[str] = Field(default_factory=list)


class CanonicalArchitecture(BaseModel):
    style: Optional[str] = None
    components: List[str] = Field(default_factory=list)
    data_stores: List[str] = Field(default_factory=list)
    async_mechanisms: List[str] = Field(default_factory=list)
    infra_notes: List[str] = Field(default_factory=list)
    key_decisions: List[str] = Field(default_factory=list)


class ArchitectureOutput(BaseModel):
    requirements: Requirements
    assumptions: List[str]

    architecture_options: List[ArchitectureOption]
    tradeoffs: Any = Field(default_factory=dict)
    recommended: Dict[str, Any] = Field(default_factory=dict)

    diagram: Any = Field(default_factory=dict)  # {"type":"mermaid","content":"..."}
    implementation_plan: Any = Field(default_factory=dict)
    open_questions: List[str] = Field(default_factory=list)

    canonical: CanonicalArchitecture = Field(default_factory=CanonicalArchitecture)
    delta: Optional[DeltaView] = None


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    stage: Literal["intake", "architecture"]

    intake: Optional[IntakeDecision] = None
    impact: Optional[ImpactAnalysis] = None
    architecture: Optional[ArchitectureOutput] = None
