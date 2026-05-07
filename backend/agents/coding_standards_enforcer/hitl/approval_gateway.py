"""
Approval gateway — gates "apply this fix" actions behind explicit user
APPROVE / REJECT decisions. Decoupled so the orchestrator can delegate.
"""
from __future__ import annotations

from agents.coding_standards_enforcer.schemas import ApprovalRequest


def build_approval_request(
    session_id: str,
    proposed_code: str,
    diff: str,
    summary: str,
    remaining_violations: list,
) -> ApprovalRequest:
    return ApprovalRequest(
        session_id=session_id,
        proposed_code=proposed_code,
        diff=diff,
        summary=summary,
        remaining_violations=remaining_violations or [],
    )
