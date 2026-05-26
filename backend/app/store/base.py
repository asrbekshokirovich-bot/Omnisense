"""Storage interface for sessions + segments + vector search. Implementations: in-memory
(default, zero-setup) and pgvector (production, in-country)."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..domain import Segment, Session


class MemoryStore(ABC):
    """A multi-tenant memory store. Every read takes a tenant_id so one user can never see
    another's segments — required for /ask, /briefing, /sessions and DELETE /data to be
    safe under the (Phase-0 thin) X-User-Id auth. add_* trust the tenant_id baked into the
    Session/Segment object (set by the API layer)."""

    @abstractmethod
    def add_session(self, session: Session) -> None: ...

    @abstractmethod
    def add_segments(self, segments: list[Segment]) -> None: ...

    @abstractmethod
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
        """Return (segment, score) pairs for THIS tenant, most similar first.

        Other filters narrow recall further — e.g. "only Russian segments from this
        session captured in the last hour". tenant_id is mandatory; mixing tenants in
        the same query result would be a privacy bug.
        """

    @abstractmethod
    def list_sessions(self, tenant_id: str) -> list[Session]: ...

    @abstractmethod
    def all_segments(self, tenant_id: str) -> list[Segment]: ...

    @abstractmethod
    def delete_all(self, tenant_id: str) -> int:
        """One-tap privacy delete for this tenant. Returns count of removed segments."""

    @abstractmethod
    def delete_session(self, session_id: str, tenant_id: str) -> int:
        """Forget one meeting for this tenant. session_id misses (or wrong-tenant
        session_id) return 0 — never cross-delete."""
