"""In-memory store with pure-Python cosine search. Default backend — runs with zero infra,
ideal for the demo and tests. Multi-tenant: every read is scoped by tenant_id."""
from __future__ import annotations

import math

from ..domain import Segment, Session
from .base import MemoryStore


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


class InMemoryStore(MemoryStore):
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._segments: list[Segment] = []

    def add_session(self, session: Session) -> None:
        self._sessions[session.id] = session

    def add_segments(self, segments: list[Segment]) -> None:
        self._segments.extend(segments)

    def search(
        self,
        query_vec: list[float],
        top_k: int,
        *,
        tenant_id: str,
        lang: str | None = None,
        session_id: str | None = None,
        since: float | None = None,
        until: float | None = None,
    ) -> list[tuple[Segment, float]]:
        candidates = [s for s in self._segments if s.tenant_id == tenant_id]
        if lang is not None:
            candidates = [s for s in candidates if s.lang == lang]
        if session_id is not None:
            candidates = [s for s in candidates if s.session_id == session_id]
        if since is not None:
            candidates = [s for s in candidates if s.created_at >= since]
        if until is not None:
            candidates = [s for s in candidates if s.created_at <= until]
        scored = [(seg, _cosine(query_vec, seg.embedding)) for seg in candidates]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]

    def list_sessions(self, tenant_id: str) -> list[Session]:
        sessions = [s for s in self._sessions.values() if s.tenant_id == tenant_id]
        return sorted(sessions, key=lambda s: s.created_at, reverse=True)

    def all_segments(self, tenant_id: str) -> list[Segment]:
        return [s for s in self._segments if s.tenant_id == tenant_id]

    def delete_all(self, tenant_id: str) -> int:
        removed = sum(1 for s in self._segments if s.tenant_id == tenant_id)
        self._segments = [s for s in self._segments if s.tenant_id != tenant_id]
        self._sessions = {sid: s for sid, s in self._sessions.items() if s.tenant_id != tenant_id}
        return removed

    def delete_session(self, session_id: str, tenant_id: str) -> int:
        session = self._sessions.get(session_id)
        if session is None or session.tenant_id != tenant_id:
            return 0
        before = len(self._segments)
        self._segments = [
            s for s in self._segments
            if not (s.session_id == session_id and s.tenant_id == tenant_id)
        ]
        self._sessions.pop(session_id, None)
        return before - len(self._segments)
