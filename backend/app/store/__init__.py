"""Factory: build the configured store."""
from __future__ import annotations

from ..config import Settings
from .base import MemoryStore
from .memory import InMemoryStore


def make_store(s: Settings, dim: int | None = None) -> MemoryStore:
    """Build the configured store. `dim` overrides s.embedding_dim — pass the embedder's
    actual dim so pgvector's column matches the vectors it will receive."""
    if s.store_backend == "pgvector":
        from .pgvector import PgVectorStore
        return PgVectorStore(s.database_url, dim if dim is not None else s.embedding_dim)
    return InMemoryStore()
