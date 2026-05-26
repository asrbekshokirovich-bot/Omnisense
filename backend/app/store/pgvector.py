"""Postgres + pgvector store (production, hosted in-country). Used when OMNI_STORE=pgvector.

Schema is created on first use. Vectors use cosine distance (<=> operator). Requires the
`psycopg` driver and the pgvector extension (the infra/docker-compose.yml image ships it).

Why this is first-class (Task 3):
  - **Dim-mismatch guard.** If the segments.embedding column was created at one dim and
    we initialize against an embedder with a different dim, INSERT silently fails (or
    worse, search becomes meaningless). On startup we read the existing column dim out of
    pg_catalog and raise an actionable error if it does not match.
  - **Metadata filtering.** `search()` accepts lang / session_id / since / until — the
    in-country API for "ask within this meeting" and "ask about last hour".
  - **Per-session delete.** `delete_session()` powers "forget this conversation" without
    nuking the whole memory.
  - **One-tap delete** (`delete_all`) is unchanged.

Not exercised in the offline test suite — the in-memory store covers the contract; the
pgvector integration test (`tests/test_pgvector.py`) runs against the docker-compose stack.
"""
from __future__ import annotations

from ..domain import Segment, Session
from .base import MemoryStore


class DimMismatchError(RuntimeError):
    """Existing schema has a different embedding dim than the configured embedder."""


class PgVectorStore(MemoryStore):
    def __init__(self, dsn: str, dim: int) -> None:
        import psycopg  # lazy: only needed on the production path

        self.dim = dim
        self.conn = psycopg.connect(dsn, autocommit=True)
        self._init_schema()
        self._guard_dim()

    def _init_schema(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute(
                "CREATE TABLE IF NOT EXISTS sessions ("
                "id TEXT PRIMARY KEY, source TEXT, lang TEXT, created_at DOUBLE PRECISION)"
            )
            cur.execute(
                "CREATE TABLE IF NOT EXISTS segments ("
                "id TEXT PRIMARY KEY, session_id TEXT, speaker TEXT, text TEXT, lang TEXT, "
                "start_ms INT, end_ms INT, created_at DOUBLE PRECISION, "
                f"embedding vector({self.dim}))"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS segments_embedding_idx "
                "ON segments USING hnsw (embedding vector_cosine_ops)"
            )
            # Cheap indexes for the metadata filters in search().
            cur.execute(
                "CREATE INDEX IF NOT EXISTS segments_session_idx ON segments (session_id)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS segments_lang_idx ON segments (lang)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS segments_created_idx ON segments (created_at)"
            )

    def _guard_dim(self) -> None:
        """If the table existed before we added the extension, the embedding column may
        have a different vector dim — raise a clear error instead of silently mismatching.
        """
        with self.conn.cursor() as cur:
            # pgvector exposes typmod via format_type; parse it out of pg_attribute.
            cur.execute(
                "SELECT format_type(atttypid, atttypmod) "
                "FROM pg_attribute "
                "WHERE attrelid = 'segments'::regclass AND attname = 'embedding'"
            )
            row = cur.fetchone()
        if not row:
            return
        col_type = row[0]  # e.g. "vector(1024)"
        if "(" not in col_type:
            return
        try:
            existing = int(col_type.split("(", 1)[1].rstrip(")"))
        except ValueError:
            return
        if existing != self.dim:
            raise DimMismatchError(
                f"pgvector segments.embedding is vector({existing}) but the configured "
                f"embedder emits {self.dim}-dim vectors. Re-create the table after wiping "
                f"the store (DROP TABLE segments;) or switch back to the matching embedder."
            )

    def add_session(self, session: Session) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sessions (id, source, lang, created_at) VALUES (%s,%s,%s,%s) "
                "ON CONFLICT (id) DO NOTHING",
                (session.id, session.source, session.lang, session.created_at),
            )

    def add_segments(self, segments: list[Segment]) -> None:
        with self.conn.cursor() as cur:
            for s in segments:
                cur.execute(
                    "INSERT INTO segments (id, session_id, speaker, text, lang, start_ms, "
                    "end_ms, created_at, embedding) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (s.id, s.session_id, s.speaker, s.text, s.lang, s.start_ms, s.end_ms,
                     s.created_at, _vec(s.embedding)),
                )

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
        where: list[str] = []
        params: list = [_vec(query_vec)]  # the score expression's vector
        if lang is not None:
            where.append("lang = %s"); params.append(lang)
        if session_id is not None:
            where.append("session_id = %s"); params.append(session_id)
        if since is not None:
            where.append("created_at >= %s"); params.append(since)
        if until is not None:
            where.append("created_at <= %s"); params.append(until)
        where_sql = (" WHERE " + " AND ".join(where)) if where else ""
        params.append(_vec(query_vec))  # the ORDER BY vector
        params.append(top_k)
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, session_id, speaker, text, lang, start_ms, end_ms, created_at, "
                "1 - (embedding <=> %s) AS score FROM segments"
                f"{where_sql} ORDER BY embedding <=> %s LIMIT %s",
                tuple(params),
            )
            rows = cur.fetchall()
        out: list[tuple[Segment, float]] = []
        for r in rows:
            out.append((Segment(id=r[0], session_id=r[1], speaker=r[2], text=r[3], lang=r[4],
                                 start_ms=r[5], end_ms=r[6], created_at=r[7]), float(r[8])))
        return out

    def list_sessions(self) -> list[Session]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, source, lang, created_at FROM sessions ORDER BY created_at DESC")
            return [Session(id=r[0], source=r[1], lang=r[2], created_at=r[3]) for r in cur.fetchall()]

    def all_segments(self) -> list[Segment]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, session_id, speaker, text, lang, start_ms, end_ms, created_at FROM segments")
            return [Segment(id=r[0], session_id=r[1], speaker=r[2], text=r[3], lang=r[4],
                            start_ms=r[5], end_ms=r[6], created_at=r[7]) for r in cur.fetchall()]

    def delete_all(self) -> int:
        with self.conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM segments")
            n = cur.fetchone()[0]
            cur.execute("DELETE FROM segments")
            cur.execute("DELETE FROM sessions")
        return int(n)

    def delete_session(self, session_id: str) -> int:
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM segments WHERE session_id = %s", (session_id,))
            removed = cur.rowcount
            cur.execute("DELETE FROM sessions WHERE id = %s", (session_id,))
        return int(removed)


def _vec(values: list[float]) -> str:
    return "[" + ",".join(str(v) for v in values) + "]"
