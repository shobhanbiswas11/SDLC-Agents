from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import uuid

from app.models.schemas import ArchitectureOutput, Requirements


@dataclass
class SessionState:
    requirements: Requirements = field(default_factory=Requirements)
    requirements_history: List[Requirements] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)

    last_architecture: Optional[ArchitectureOutput] = None
    last_arch_summary: str = ""

    stage: str = "intake"  # intake | architecture


class InMemorySessionStore:
    def __init__(self) -> None:
        self._store: Dict[str, SessionState] = {}

    def get_or_create(self, session_id: Optional[str]) -> tuple[str, SessionState]:
        if session_id and session_id in self._store:
            return session_id, self._store[session_id]
        new_id = session_id or str(uuid.uuid4())
        self._store[new_id] = SessionState()
        return new_id, self._store[new_id]

    def update(self, session_id: str, state: SessionState) -> None:
        self._store[session_id] = state


session_store = InMemorySessionStore()
