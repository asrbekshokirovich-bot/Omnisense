"""Storage interface for sessions + segments + vector search. Implementations: in-memory
(default, zero-setup) and pgvector (production, in-country)."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..domain import Segment, Session


class MemoryStore(ABC):
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
        lang: str | None = None,
        session_id: str | None = None,
        since: float | None = None,
        until: float | None = None,
    ) -> list[tuple[Segment, float]]:
        """Return (segment, score) pairs, most similar first.

        Optional filters narrow recall — e.g. "only Russian segments from this session
        captured in the last hour". Mandatory for the eventual "ask within this meeting"
        UX and for the residency/forensics audit log.
        """

    @abstractmethod
    def list_sessions(self) -> list[Session]: ...

    @abstractmethod
    def all_segments(self) -> list[Segment]: ...

    @abstractmethod
    def delete_all(self) -> int:
        """Delete everything (one-tap privacy). Returns count of removed segments."""

    @abstractmethod
    def delete_session(self, session_id: str) -> int:
        """Forget one meeting. Returns count of removed segments (0 if unknown)."""
