"""Factory: build the configured store."""
from __future__ import annotations

from ..config import Settings
from .base import MemoryStore
from .memory import InMemoryStore


def make_store(s: Settings) -> MemoryStore:
    if s.store_backend == "pgvector":
        from .pgvector import PgVectorStore
        return PgVectorStore(s.database_url, s.embedding_dim)
    return InMemoryStore()
