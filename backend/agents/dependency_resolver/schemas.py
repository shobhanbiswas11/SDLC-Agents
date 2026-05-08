"""
Pydantic schemas for the Dependency Resolver Agent.
Covers both headless REST and HITL WebSocket paths.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

# ─── Ecosystem / strategy enums ───────────────────────────────────────────────

Ecosystem = Literal["pypi", "npm", "maven", "cargo"]
Strategy  = Literal["latest", "minimal", "stable"]


# ─── Core resolver schemas ────────────────────────────────────────────────────

class ResolveRequest(BaseModel):
    ecosystem: Ecosystem            = Field(..., description="Package ecosystem")
    manifest: str                   = Field(..., description="Raw manifest file contents")
    strategy: Strategy              = Field("stable", description="Version selection strategy")
    include_dev: bool               = Field(False, description="Include dev/optional dependencies")
    explain: bool                   = Field(True,  description="Use LLM to explain conflicts")
    check_vulnerabilities: bool     = Field(True,  description="Query OSV.dev for CVEs")


class ResolvedPackage(BaseModel):
    name: str
    version: str
    direct: bool
    parents: List[str]              = Field(default_factory=list)
    license: Optional[str]          = None
    vulnerabilities: List[str]      = Field(default_factory=list)   # CVE / GHSA ids
    deprecated: bool                = False


class Conflict(BaseModel):
    package: str
    requested_by: Dict[str, str]                # requester → constraint
    resolution: Optional[str]       = None      # version chosen by solver
    explanation: Optional[str]      = None      # filled by LLM explainer


class ResolveResponse(BaseModel):
    ok: bool
    resolved: List[ResolvedPackage]             = Field(default_factory=list)
    conflicts: List[Conflict]                   = Field(default_factory=list)
    lockfile: str                               = ""
    report_markdown: str                        = ""
    trace_id: str                               = Field(default_factory=lambda: str(uuid.uuid4()))


class DiffRequest(BaseModel):
    old: ResolveRequest
    new: ResolveRequest


class DiffResponse(BaseModel):
    added: List[ResolvedPackage]    = Field(default_factory=list)
    removed: List[ResolvedPackage]  = Field(default_factory=list)
    upgraded: List[Dict[str, Any]]  = Field(default_factory=list)
    downgraded: List[Dict[str, Any]]= Field(default_factory=list)
    unchanged: int                  = 0
    trace_id: str                   = Field(default_factory=lambda: str(uuid.uuid4()))


class AuditResponse(BaseModel):
    total_packages: int             = 0
    vulnerable: List[ResolvedPackage] = Field(default_factory=list)
    license_issues: List[Dict[str, str]] = Field(default_factory=list)
    report_markdown: str            = ""
    trace_id: str                   = Field(default_factory=lambda: str(uuid.uuid4()))


# ─── HITL session schemas ─────────────────────────────────────────────────────

class SessionStatus(str, Enum):
    CREATED          = "created"
    ACTIVE           = "active"
    PENDING_APPROVAL = "pending_approval"
    APPROVED         = "approved"
    REJECTED         = "rejected"
    CLOSED           = "closed"


class MessageType(str, Enum):
    USER_MESSAGE      = "user_message"
    AGENT_MESSAGE     = "agent_message"
    SEARCH_EVENT      = "search_event"
    SOLVER_EVENT      = "solver_event"
    APPROVAL_REQUEST  = "approval_request"
    APPROVAL_RESPONSE = "approval_response"
    SYSTEM            = "system"
    ERROR             = "error"


class ChatMessage(BaseModel):
    message_id: str                 = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    type: MessageType
    timestamp: datetime             = Field(default_factory=datetime.utcnow)
    payload: Dict[str, Any]         = Field(default_factory=dict)
    done: bool                      = True   # for streaming agent_message fragments


class SearchResult(BaseModel):
    query: str
    url: str
    title: str
    snippet: str
    fetched_at: datetime            = Field(default_factory=datetime.utcnow)


class ApprovalRequest(BaseModel):
    approval_id: str                = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    proposed_lockfile: str
    report_markdown: str
    conflicts: List[Conflict]       = Field(default_factory=list)
    search_citations: List[SearchResult] = Field(default_factory=list)
    stats: Dict[str, Any]           = Field(default_factory=dict)


class ApprovalResponse(BaseModel):
    approval_id: str
    session_id: str
    decision: Literal["APPROVE", "REJECT"]
    comment: Optional[str]          = None
    decided_at: datetime            = Field(default_factory=datetime.utcnow)


class HITLSession(BaseModel):
    session_id: str                 = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str]          = None
    ecosystem: Ecosystem
    manifest: str
    strategy: Strategy              = "stable"
    status: SessionStatus           = SessionStatus.CREATED
    title: Optional[str]            = None
    created_at: datetime            = Field(default_factory=datetime.utcnow)
    updated_at: datetime            = Field(default_factory=datetime.utcnow)
    messages: List[ChatMessage]     = Field(default_factory=list)
    pending_approval: Optional[ApprovalRequest] = None
    trace_ids: List[str]            = Field(default_factory=list)
    # Snapshot of last successful resolution — survives approval/rejection
    resolution_stats: dict          = Field(default_factory=dict)


class CreateSessionRequest(BaseModel):
    ecosystem: Ecosystem
    manifest: str
    strategy: Strategy              = "stable"
    user_id: Optional[str]          = None


class CreateSessionResponse(BaseModel):
    session_id: str
    websocket_url: str
    status: SessionStatus           = SessionStatus.CREATED
    created_at: datetime            = Field(default_factory=datetime.utcnow)


# ─── WebSocket envelope ───────────────────────────────────────────────────────

class WSMessage(BaseModel):
    """Typed WebSocket envelope — every frame on the wire uses this shape."""
    type: MessageType
    session_id: str
    message_id: str                 = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str                  = Field(default_factory=lambda: datetime.utcnow().isoformat())
    payload: Dict[str, Any]         = Field(default_factory=dict)
    done: bool                      = True
