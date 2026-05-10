"""
HITL API Routes
----------------
Endpoints for human-in-the-loop approval flow.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.hitl_manager import submit_response, get_pending_approval

router = APIRouter(prefix="/api/hitl", tags=["hitl"])


class ApprovalResponse(BaseModel):
    decision: str  # "approve" | "reject" | "modify"
    modified_command: Optional[str] = None


@router.post("/{task_id}/respond")
def respond_to_approval(task_id: str, body: ApprovalResponse):
    """
    User submits their approval/rejection for a proposed fix.
    """
    if body.decision not in ("approve", "reject", "modify"):
        raise HTTPException(
            status_code=400,
            detail="decision must be 'approve', 'reject', or 'modify'"
        )

    if body.decision == "modify" and not body.modified_command:
        raise HTTPException(
            status_code=400,
            detail="modified_command is required when decision is 'modify'"
        )

    submit_response(
        task_id=task_id,
        decision=body.decision,
        modified_command=body.modified_command,
    )

    return {"status": "ok", "task_id": task_id, "decision": body.decision}


@router.get("/{task_id}/pending")
def get_pending(task_id: str):
    """
    Returns the current pending approval request for a task.
    """
    pending = get_pending_approval(task_id)

    if not pending:
        return {"status": "no_pending", "task_id": task_id}

    return {"status": "pending", "task_id": task_id, "details": pending}
