"""Postgres + pgvector store (production, hosted in-country). Used when OMNI_STORE=pgvector.

Schema is created on first use. Vectors use cosine distance (<=> operator). Requires the
`psycopg` driver and the pgvector extension (the infra/docker-compose.yml image ships it).
Not exercised in the offline demo — the in-memory store covers that.
"""
from __future__ import annotations

from ..domain import Segment, Session
from .base import MemoryStore


class PgVectorStore(MemoryStore):
    def __init__(self, dsn: str, dim: int) -> None:
        import psycopg  # lazy: only needed on the production path

        self.dim = dim
        self.conn = psycopg.connect(dsn, autocommit=True)
        self._init_schema()

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

    def search(self, query_vec: list[float], top_k: int) -> list[tuple[Segment, float]]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, session_id, speaker, text, lang, start_ms, end_ms, created_at, "
                "1 - (embedding <=> %s) AS score FROM segments ORDER BY embedding <=> %s LIMIT %s",
                (_vec(query_vec), _vec(query_vec), top_k),
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


def _vec(values: list[float]) -> str:
    return "[" + ",".join(str(v) for v in values) + "]"
