from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class Session:
    id: str
    messages: list[dict[str, str]] = field(default_factory=list)


_sessions: dict[str, Session] = {}


def create_session() -> Session:
    session = Session(id=str(uuid.uuid4()))
    _sessions[session.id] = session
    return session


def get_session(session_id: str) -> Session | None:
    return _sessions.get(session_id)
