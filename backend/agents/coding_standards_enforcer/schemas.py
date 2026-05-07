"""
Pydantic schemas for the Coding Standards Enforcer agent.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────
# Request bodies
# ─────────────────────────────────────────────────────────────


class ScanRequest(BaseModel):
    repo_url: str = ""
    local_path: str = ""


class AnalyzeRequest(BaseModel):
    """Live single-file analysis."""
    code: str
    language: str  # python, cpp, java, javascript, typescript, go, rust


class FixAllRequest(BaseModel):
    """Fix all violations in a code blob."""
    code: str
    language: str
    violations: List[Dict[str, Any]] = Field(default_factory=list)


class PolishRequest(BaseModel):
    """Run an iterative analyze+fix loop with deterministic post-processing.

    Goal: return code that the analyser reports as having zero violations.
    """
    code: str
    language: str
    max_passes: int = 5


class CloneRepoRequest(BaseModel):
    """Clone (or load) a repo and return source files for the editor."""
    repo_url: str = ""
    local_path: str = ""
    branch: str = ""


class RepoBranchesRequest(BaseModel):
    repo_url: str


class ApplyLintersRequest(BaseModel):
    repo_path: str


# ─────────────────────────────────────────────────────────────
# Response payloads
# ─────────────────────────────────────────────────────────────


class Violation(BaseModel):
    line: int = 0
    column: int = 1
    rule_code: str = "STYLE"
    rule_standard: str = "Coding Standard"
    rule_description: str = ""
    message: str = ""
    severity: str = "warning"
    original_code: str = ""
    suggested_code: str = ""
    explanation: str = ""
    diff: str = ""


class AnalyzeResponse(BaseModel):
    language: str
    violations: List[Violation] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)


class FixAllResponse(BaseModel):
    explanation: str
    fixed_code: str
    diff: str


class PolishResponse(BaseModel):
    fixed_code: str
    diff: str
    passes_used: int
    remaining_violations: List[Dict[str, Any]] = Field(default_factory=list)
    history: List[Dict[str, Any]] = Field(default_factory=list)


class FileEntry(BaseModel):
    content: str
    language: str
    size_bytes: int


class RepoFilesResponse(BaseModel):
    repo_path: str
    total_files: int
    files: Dict[str, FileEntry]


class Branch(BaseModel):
    name: str
    sha: str


class RepoBranchesResponse(BaseModel):
    branches: List[Branch]
    total: int


class LanguageInfo(BaseModel):
    key: str
    name: str
    standards: List[str]
    categories: List[str]


class LanguagesResponse(BaseModel):
    languages: List[LanguageInfo]


class ApplyLintersResponse(BaseModel):
    tools_applied: List[str]
    remaining_violations: int
    violations: List[Dict[str, Any]]


class HealthResponse(BaseModel):
    status: str


# ─────────────────────────────────────────────────────────────
# HITL — chat-style assistant for resolving violations
# ─────────────────────────────────────────────────────────────


class SessionStatus(str, Enum):
    CREATED = "created"
    ACTIVE = "active"
    PENDING_APPROVAL = "pending_approval"
    CLOSED = "closed"


class MessageType(str, Enum):
    USER_MESSAGE = "user_message"          # incoming chat from the user
    AGENT_MESSAGE = "agent_message"        # streamed assistant tokens
    ANALYZE_EVENT = "analyze_event"        # a /analyze pipeline notice
    POLISH_EVENT = "polish_event"          # a /polish pipeline notice
    APPROVAL_REQUEST = "approval_request"  # propose to apply a fix
    APPROVAL_RESPONSE = "approval_response"  # user's APPROVE / REJECT
    SYSTEM = "system"                      # generic notices, titles
    ERROR = "error"


class ChatMessage(BaseModel):
    """A single frame stored in the session history."""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    type: MessageType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: Dict[str, Any] = Field(default_factory=dict)
    done: bool = True  # for streaming agent_message fragments


class ApprovalRequest(BaseModel):
    """The agent proposes applying a polished fix; user must APPROVE."""
    approval_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    proposed_code: str
    diff: str = ""
    summary: str = ""
    remaining_violations: List[Dict[str, Any]] = Field(default_factory=list)


class ApprovalResponse(BaseModel):
    approval_id: str
    session_id: str
    decision: Literal["APPROVE", "REJECT"]
    comment: Optional[str] = None
    decided_at: datetime = Field(default_factory=datetime.utcnow)


class HITLSession(BaseModel):
    """Persistent record of one chat conversation about a code blob."""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    language: str = "python"
    code: str = ""
    last_polished_code: Optional[str] = None
    title: Optional[str] = None
    status: SessionStatus = SessionStatus.CREATED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    messages: List[ChatMessage] = Field(default_factory=list)
    pending_approval: Optional[ApprovalRequest] = None


class CreateSessionRequest(BaseModel):
    code: str
    language: str
    user_id: Optional[str] = None
    title: Optional[str] = None


class CreateSessionResponse(BaseModel):
    session_id: str
    websocket_url: str
    status: SessionStatus = SessionStatus.CREATED
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WSMessage(BaseModel):
    """Typed WebSocket envelope — every frame on the wire uses this shape."""
    type: MessageType
    session_id: str
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    payload: Dict[str, Any] = Field(default_factory=dict)
    done: bool = True
