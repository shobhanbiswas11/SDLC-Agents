"""
JSON-backed session store for HITL chats.

Each session is mirrored to ``backend/state/hitl/<session_id>.json`` so a
server restart doesn't drop conversations, and so debugging can use plain
``cat`` / ``jq`` against the file.

The in-process dict is the source of truth at runtime; the JSON is a
write-through cache.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

from agents.coding_standards_enforcer.schemas import (
    ChatMessage,
    HITLSession,
    MessageType,
    SessionStatus,
)

logger = logging.getLogger(__name__)


_STATE_DIR = os.path.join(os.getcwd(), "state", "hitl")
os.makedirs(_STATE_DIR, exist_ok=True)


# session_id → HITLSession
_SESSIONS: Dict[str, HITLSession] = {}


# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────


def create_session(
    session_id: str,
    code: str,
    language: str,
    user_id: Optional[str] = None,
    title: Optional[str] = None,
) -> HITLSession:
    session = HITLSession(
        session_id=session_id,
        user_id=user_id,
        language=language,
        code=code,
        title=title,
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


def list_sessions() -> List[HITLSession]:
    """Return all known sessions, loading from disk if not cached."""
    seen: Dict[str, HITLSession] = dict(_SESSIONS)
    for fname in os.listdir(_STATE_DIR):
        if not fname.endswith(".json"):
            continue
        sid = fname[:-5]
        if sid in seen:
            continue
        s = _load(sid)
        if s:
            seen[sid] = s
    return sorted(seen.values(), key=lambda s: s.updated_at, reverse=True)


def delete_session(session_id: str) -> bool:
    """Forget a session entirely, including its JSON file."""
    _SESSIONS.pop(session_id, None)
    path = os.path.join(_STATE_DIR, f"{session_id}.json")
    if os.path.exists(path):
        try:
            os.remove(path)
            return True
        except Exception as exc:
            logger.warning("Could not delete %s: %s", path, exc)
    return False


def get_history(session: HITLSession) -> List[dict]:
    """Compact list of (role, text) pairs suitable for an LLM context."""
    return [
        {
            "role": "user"
            if m.type == MessageType.USER_MESSAGE
            else "assistant",
            "content": m.payload.get("text", ""),
        }
        for m in session.messages
        if m.type in (MessageType.USER_MESSAGE, MessageType.AGENT_MESSAGE)
        and m.payload.get("text")
    ]


# ─────────────────────────────────────────────────────────────
# JSON persistence
# ─────────────────────────────────────────────────────────────


def _persist(session: HITLSession) -> None:
    path = os.path.join(_STATE_DIR, f"{session.session_id}.json")
    try:
        with open(path, "w") as f:
            f.write(session.model_dump_json(indent=2))
    except Exception as exc:
        logger.warning("Could not persist session %s: %s", session.session_id, exc)


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
    except Exception as exc:
        logger.warning("Could not load session %s: %s", session_id, exc)
        return None
