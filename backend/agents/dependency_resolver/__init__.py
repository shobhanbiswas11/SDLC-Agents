"""
Dependency Resolver Agent — FastAPI router.

REST endpoints  : /resolve  /diff  /audit  /health
HITL endpoints  : /session  /session/{id}  /session/{id}/approve  DELETE /session/{id}
WebSocket       : /chat/{session_id}
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect, status

from agents.dependency_resolver.agent import execute_resolve, execute_diff, execute_audit
from agents.dependency_resolver.schemas import (
    ResolveRequest, ResolveResponse,
    DiffRequest, DiffResponse,
    AuditResponse,
    CreateSessionRequest, CreateSessionResponse,
    ApprovalResponse,
    MessageType,
)
from agents.dependency_resolver.hitl.orchestrator import HITLOrchestrator

logger = logging.getLogger(__name__)

agent_router = APIRouter(
    prefix="/dependency_resolver",
    tags=["Dependency Resolver"],
)

_orchestrator = HITLOrchestrator()


# ── Headless REST ─────────────────────────────────────────────────────────────

@agent_router.post("/resolve", response_model=ResolveResponse, summary="Resolve a manifest (headless / CI)")
async def resolve(payload: ResolveRequest):
    try:
        return await execute_resolve(payload)
    except NotImplementedError as e:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@agent_router.post("/diff", response_model=DiffResponse, summary="Diff two manifests")
async def diff(payload: DiffRequest):
    try:
        return await execute_diff(payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@agent_router.post("/audit", response_model=AuditResponse, summary="CVE + license audit")
async def audit(payload: ResolveRequest):
    try:
        return await execute_audit(payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@agent_router.get("/health", summary="Liveness check")
async def health():
    return await _orchestrator.health_check()


# ── HITL Session REST ─────────────────────────────────────────────────────────

@agent_router.post("/session", response_model=CreateSessionResponse, summary="Create HITL session")
async def create_session(payload: CreateSessionRequest, request: Request):
    base = str(request.base_url).rstrip("/")
    return await _orchestrator.create_session(payload, base_url=base)


@agent_router.get("/session/{session_id}", summary="Get session + message history")
async def get_session(session_id: str):
    data = await _orchestrator.get_session_data(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    return data


@agent_router.post("/session/{session_id}/approve", summary="REST fallback for APPROVE/REJECT")
async def approve(session_id: str, payload: ApprovalResponse):
    try:
        await _orchestrator.handle_rest_approval(session_id, payload)
        return {"status": "ok", "decision": payload.decision}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@agent_router.delete("/session/{session_id}", summary="Close / abort session")
async def close_session(session_id: str):
    return await _orchestrator.close_session(session_id)


# ── WebSocket HITL ────────────────────────────────────────────────────────────

@agent_router.websocket("/chat/{session_id}")
async def hitl_chat(websocket: WebSocket, session_id: str):
    """
    Real-time bidirectional HITL channel.

    Frame format (JSON):
      { "type": "<MessageType>", "session_id": "…", "payload": { … }, "done": true }

    To send a message:
      { "type": "user_message", "session_id": "…", "payload": { "text": "…" } }

    To approve:
      { "type": "approval_response", "session_id": "…",
        "payload": { "decision": "APPROVE", "comment": "LGTM" } }
    """
    await _orchestrator.connect(websocket, session_id)
    try:
        while True:
            raw_text = await websocket.receive_text()

            if len(raw_text) > 65_536:
                await _orchestrator._emit(session_id, MessageType.ERROR,
                                          {"text": "Message too large (max 64KB)."})
                continue

            try:
                raw = json.loads(raw_text)
            except (json.JSONDecodeError, ValueError):
                await _orchestrator._emit(session_id, MessageType.ERROR,
                                          {"text": "Invalid JSON."})
                continue

            try:
                await _orchestrator.handle_message(session_id, raw)
            except Exception as exc:
                logger.exception(f"handle_message error session={session_id}")
                await _orchestrator._emit(session_id, MessageType.ERROR,
                                          {"text": f"Error processing message: {exc}"})

    except WebSocketDisconnect:
        await _orchestrator.disconnect(session_id)
    except Exception as exc:
        logger.error(f"WS error session={session_id}: {exc}")
        try:
            await websocket.close(code=1011, reason=str(exc)[:120])
        except Exception:
            pass
        await _orchestrator.disconnect(session_id)
