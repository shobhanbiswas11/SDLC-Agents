"""
HITL Session model and in-memory store.
Sessions persist message history and approval state.
"""
from __future__ import annotations
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from agents.dependency_resolver.schemas import (
    HITLSession, ChatMessage, MessageType, SessionStatus,
    ApprovalRequest, WSMessage,
)

_STATE_DIR = os.path.join(os.getcwd(), "state", "hitl")
os.makedirs(_STATE_DIR, exist_ok=True)

# In-process store: session_id → HITLSession
_SESSIONS: Dict[str, HITLSession] = {}


def create_session(
    session_id: str,
    ecosystem: str,
    manifest: str,
    strategy: str = "stable",
    user_id: Optional[str] = None,
) -> HITLSession:
    session = HITLSession(
        session_id=session_id,
        user_id=user_id,
        ecosystem=ecosystem,  # type: ignore[arg-type]
        manifest=manifest,
        strategy=strategy,  # type: ignore[arg-type]
        status=SessionStatus.CREATED,
    )
    _SESSIONS[session_id] = session
    _persist(session)
    return session


def get_session(session_id: str) -> Optional[HITLSession]:
    if session_id in _SESSIONS:
        return _SESSIONS[session_id]
    return _load(session_id)


def save_session(session: HITLSession) -> None:
    session.updated_at = datetime.utcnow()
    _SESSIONS[session.session_id] = session
    _persist(session)


def add_message(session: HITLSession, msg: ChatMessage) -> None:
    session.messages.append(msg)
    save_session(session)


def get_history(session: HITLSession) -> List[dict]:
    return [
        {"role": "user" if m.type == MessageType.USER_MESSAGE else "assistant",
         "content": m.payload.get("text", "")}
        for m in session.messages
        if m.type in (MessageType.USER_MESSAGE, MessageType.AGENT_MESSAGE)
        and m.payload.get("text")
    ]


def _persist(session: HITLSession) -> None:
    path = os.path.join(_STATE_DIR, f"{session.session_id}.json")
    try:
        with open(path, "w") as f:
            f.write(session.model_dump_json(indent=2))
    except Exception:
        pass


def _load(session_id: str) -> Optional[HITLSession]:
    path = os.path.join(_STATE_DIR, f"{session_id}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        session = HITLSession(**data)
        _SESSIONS[session_id] = session
        return session
    except Exception:
        return None
