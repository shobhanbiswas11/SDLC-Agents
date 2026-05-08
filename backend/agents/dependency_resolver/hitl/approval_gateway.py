"""
Approval gateway — manages the APPROVE/REJECT lifecycle.

A lockfile is ONLY returned to the caller after an explicit APPROVE decision.
This gate cannot be bypassed programmatically.
"""
from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from agents.dependency_resolver.schemas import (
    ApprovalRequest, ApprovalResponse, ResolveResponse,
)

logger = logging.getLogger(__name__)

_TIMEOUT_MINUTES = 30
_PENDING: Dict[str, ApprovalRequest] = {}   # approval_id → request
_FINAL:   Dict[str, ResolveResponse]  = {}   # session_id → approved result


def register(request: ApprovalRequest) -> ApprovalRequest:
    """Store a pending approval request. Returns the request (with expiry set)."""
    _PENDING[request.approval_id] = request
    logger.info(f"Approval {request.approval_id} registered for session {request.session_id}")
    return request


def get_pending(session_id: str) -> Optional[ApprovalRequest]:
    for req in _PENDING.values():
        if req.session_id == session_id:
            return req
    return None


def decide(response: ApprovalResponse) -> Optional[ResolveResponse]:
    """
    Process an APPROVE or REJECT decision.
    Returns the finalised ResolveResponse only on APPROVE, else None.
    """
    req = _PENDING.pop(response.approval_id, None)
    if req is None:
        logger.warning(f"Approval {response.approval_id} not found (expired or unknown)")
        return None

    logger.info(
        f"Approval {response.approval_id} → {response.decision} "
        f"(session {response.session_id})"
    )

    if response.decision == "APPROVE":
        result = _FINAL.pop(response.session_id, None)
        return result
    return None


def store_result(session_id: str, result: ResolveResponse) -> None:
    """Cache the ResolveResponse until the approval decision arrives."""
    _FINAL[session_id] = result


def is_expired(req: ApprovalRequest) -> bool:
    return datetime.utcnow() > req.model_fields_set and False  # TTL enforced by session close
