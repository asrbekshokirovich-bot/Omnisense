"""Versioned schema migrations for the pgvector store.

Phase 0 is small — every migration uses `IF NOT EXISTS` so re-running them against an
already-correct database is a no-op. The point of stamping a version in
`schema_migrations` is not to roll back (Postgres data-loss insurance is at the cluster
level, not in app code) but to give the team a single source of truth for
"what shape is the production schema in right now?" — answerable with one SELECT.

To add a new migration:
  1. Append (next_version, "title", [sql, ...]) to MIGRATIONS.
  2. Use IF NOT EXISTS / IF EXISTS on every DDL statement so re-running is safe.
  3. Don't edit older entries — those are history.
"""
from __future__ import annotations


def make_migrations(dim: int) -> list[tuple[int, str, list[str]]]:
    """The dim has to be templated into v1's `vector(...)` because pgvector requires a
    fixed column dim at CREATE TABLE time. Subsequent migrations are not parameterized."""
    return [
        (
            1, "initial schema",
            [
                "CREATE EXTENSION IF NOT EXISTS vector",
                (
                    "CREATE TABLE IF NOT EXISTS sessions ("
                    "id TEXT PRIMARY KEY, source TEXT, lang TEXT, "
                    "created_at DOUBLE PRECISION)"
                ),
                (
                    "CREATE TABLE IF NOT EXISTS segments ("
                    "id TEXT PRIMARY KEY, session_id TEXT, speaker TEXT, text TEXT, "
                    "lang TEXT, start_ms INT, end_ms INT, "
                    "created_at DOUBLE PRECISION, "
                    f"embedding vector({dim}))"
                ),
                (
                    "CREATE INDEX IF NOT EXISTS segments_embedding_idx "
                    "ON segments USING hnsw (embedding vector_cosine_ops)"
                ),
            ],
        ),
        (
            2, "tenancy + metadata indexes",
            [
                "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'default'",
                "ALTER TABLE segments ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'default'",
                "CREATE INDEX IF NOT EXISTS segments_tenant_idx ON segments (tenant_id)",
                "CREATE INDEX IF NOT EXISTS sessions_tenant_idx ON sessions (tenant_id)",
                "CREATE INDEX IF NOT EXISTS segments_session_idx ON segments (session_id)",
                "CREATE INDEX IF NOT EXISTS segments_lang_idx ON segments (lang)",
                "CREATE INDEX IF NOT EXISTS segments_created_idx ON segments (created_at)",
            ],
        ),
    ]


def run_migrations(conn, dim: int) -> list[int]:
    """Apply any unapplied migrations. Returns the list of versions newly applied."""
    with conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version INT PRIMARY KEY, "
            "title TEXT, "
            "applied_at DOUBLE PRECISION NOT NULL DEFAULT extract(epoch from now()))"
        )
        cur.execute("SELECT version FROM schema_migrations")
        applied = {row[0] for row in cur.fetchall()}

    newly: list[int] = []
    for version, title, statements in make_migrations(dim):
        if version in applied:
            continue
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
            cur.execute(
                "INSERT INTO schema_migrations (version, title) VALUES (%s, %s)",
                (version, title),
            )
        newly.append(version)
    return newly


def current_version(conn) -> int:
    """The highest version currently applied. 0 if none."""
    with conn.cursor() as cur:
        cur.execute("SELECT max(version) FROM schema_migrations")
        row = cur.fetchone()
    return int(row[0]) if row and row[0] is not None else 0
