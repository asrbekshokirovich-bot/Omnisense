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
    def __init__(self, dsn: str, dim: int, *, connect=None) -> None:
        """Create / open the store.

        `connect` is an optional override for `psycopg.connect`; production uses the
        default (psycopg), tests can inject the in-memory fake from
        `tests.fakes.fake_psycopg` to exercise the store offline.
        """
        if connect is None:
            import psycopg  # lazy: only needed on the production path
            connect = psycopg.connect

        self.dim = dim
        self.conn = connect(dsn, autocommit=True)
        from ._pg_migrations import run_migrations
        self.applied = run_migrations(self.conn, dim)
        self._guard_dim()

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
                "INSERT INTO sessions (id, source, lang, tenant_id, created_at) "
                "VALUES (%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                (session.id, session.source, session.lang, session.tenant_id, session.created_at),
            )

    def add_segments(self, segments: list[Segment]) -> None:
        with self.conn.cursor() as cur:
            for s in segments:
                cur.execute(
                    "INSERT INTO segments (id, session_id, speaker, text, lang, tenant_id, "
                    "start_ms, end_ms, created_at, embedding) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (s.id, s.session_id, s.speaker, s.text, s.lang, s.tenant_id,
                     s.start_ms, s.end_ms, s.created_at, _vec(s.embedding)),
                )

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
        where: list[str] = ["tenant_id = %s"]
        params: list = [_vec(query_vec), tenant_id]
        if lang is not None:
            where.append("lang = %s"); params.append(lang)
        if session_id is not None:
            where.append("session_id = %s"); params.append(session_id)
        if since is not None:
            where.append("created_at >= %s"); params.append(since)
        if until is not None:
            where.append("created_at <= %s"); params.append(until)
        where_sql = " WHERE " + " AND ".join(where)
        params.append(_vec(query_vec))  # the ORDER BY vector
        params.append(top_k)
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, session_id, speaker, text, lang, tenant_id, start_ms, end_ms, "
                "created_at, 1 - (embedding <=> %s) AS score FROM segments"
                f"{where_sql} ORDER BY embedding <=> %s LIMIT %s",
                tuple(params),
            )
            rows = cur.fetchall()
        out: list[tuple[Segment, float]] = []
        for r in rows:
            out.append((Segment(id=r[0], session_id=r[1], speaker=r[2], text=r[3], lang=r[4],
                                 tenant_id=r[5], start_ms=r[6], end_ms=r[7],
                                 created_at=r[8]), float(r[9])))
        return out

    def list_sessions(self, tenant_id: str) -> list[Session]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, source, lang, tenant_id, created_at FROM sessions "
                "WHERE tenant_id = %s ORDER BY created_at DESC",
                (tenant_id,),
            )
            return [Session(id=r[0], source=r[1], lang=r[2], tenant_id=r[3], created_at=r[4])
                    for r in cur.fetchall()]

    def all_segments(self, tenant_id: str) -> list[Segment]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, session_id, speaker, text, lang, tenant_id, start_ms, end_ms, "
                "created_at FROM segments WHERE tenant_id = %s",
                (tenant_id,),
            )
            return [Segment(id=r[0], session_id=r[1], speaker=r[2], text=r[3], lang=r[4],
                            tenant_id=r[5], start_ms=r[6], end_ms=r[7], created_at=r[8])
                    for r in cur.fetchall()]

    def delete_all(self, tenant_id: str) -> int:
        with self.conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM segments WHERE tenant_id = %s", (tenant_id,))
            n = cur.fetchone()[0]
            cur.execute("DELETE FROM segments WHERE tenant_id = %s", (tenant_id,))
            cur.execute("DELETE FROM sessions WHERE tenant_id = %s", (tenant_id,))
        return int(n)

    def delete_session(self, session_id: str, tenant_id: str) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                "DELETE FROM segments WHERE session_id = %s AND tenant_id = %s",
                (session_id, tenant_id),
            )
            removed = cur.rowcount
            cur.execute(
                "DELETE FROM sessions WHERE id = %s AND tenant_id = %s",
                (session_id, tenant_id),
            )
        return int(removed)


def _vec(values: list[float]) -> str:
    return "[" + ",".join(str(v) for v in values) + "]"
