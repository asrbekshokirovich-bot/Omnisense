"""A tiny in-memory psycopg fake — just enough surface to exercise PgVectorStore
without Docker / Postgres / pgvector.

Why this exists: the integration test in tests/test_pgvector.py is the right way to
verify real semantics (real pgvector cosine, real ALTER COLUMN semantics) but it needs
the docker-compose stack. The team should still get fast confidence that the store's
SQL *shape* is correct on every commit — that is what this fake gives them.

Scope:
  - The SQL statements PgVectorStore + the migrations module emit. Nothing else.
  - Cosine search is computed in Python over the rows the test inserted.
  - Each call to `connect(dsn, ...)` returns a fresh DB unless the dsn is reused via
    `Database.attach(dsn, db)`, which lets a test share state across reconnects (used
    by the dim-mismatch test).

Non-goals:
  - General SQL parser. Anything outside the patterns below raises NotImplementedError
    so silently-wrong tests are impossible.
  - HNSW index behavior. CREATE INDEX is a no-op; ranking is a Python sort.
"""
from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass, field


# ---- shared DSN registry ----------------------------------------------------
_REGISTRY: dict[str, "Database"] = {}


@dataclass
class Database:
    """The in-memory state for one DSN."""
    dim: int | None = None
    sessions: list[dict] = field(default_factory=list)
    segments: list[dict] = field(default_factory=list)
    schema_migrations: list[dict] = field(default_factory=list)  # [{version, title, applied_at}]
    tables: set[str] = field(default_factory=set)


def attach(dsn: str, db: Database | None = None) -> Database:
    """Bind a DSN to a Database. Subsequent connect()s reuse it. Returns the bound db."""
    db = db or Database()
    _REGISTRY[dsn] = db
    return db


def reset() -> None:
    """Drop every registered DSN. Tests can call this in teardown."""
    _REGISTRY.clear()


def connect(dsn: str, *args, **kwargs) -> "FakeConnection":
    """The psycopg.connect lookalike. Reuses the Database for the same DSN so a
    'reconnect' sees the same state — that's how PgVectorStore's dim-mismatch test
    works (open at dim=4, close, re-open at dim=8 → mismatch)."""
    if dsn not in _REGISTRY:
        _REGISTRY[dsn] = Database()
    return FakeConnection(_REGISTRY[dsn])


# ---- connection / cursor ---------------------------------------------------
class FakeConnection:
    def __init__(self, db: Database) -> None:
        self.db = db

    def cursor(self) -> "FakeCursor":
        return FakeCursor(self.db)

    def close(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_) -> None:
        return None


_VEC = re.compile(r"vector\((\d+)\)")


def _parse_vec_str(s: str) -> list[float]:
    """`PgVectorStore._vec` writes '[1.0,0.0,...]' — round-trip back to floats."""
    s = s.strip()
    if not s.startswith("[") or not s.endswith("]"):
        raise ValueError(f"not a vector literal: {s!r}")
    return [float(x) for x in s[1:-1].split(",") if x.strip()]


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


class FakeCursor:
    """Pattern-matches the exact SQL PgVectorStore + the migrations module emit.
    Anything else is NotImplementedError — silent partial coverage would be worse than
    no coverage."""

    def __init__(self, db: Database) -> None:
        self.db = db
        self._rows: list[tuple] = []
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, *_) -> None:
        return None

    # --- the dispatch table -------------------------------------------------
    def execute(self, sql: str, params: tuple | list | None = None) -> None:
        params = tuple(params or ())
        s = " ".join(sql.split()).strip()
        sl = s.lower()
        # Migrations + DDL ---------------------------------------------------
        if sl.startswith("create extension"):
            return
        if sl.startswith("create index"):
            return
        if sl.startswith("create table if not exists sessions"):
            self.db.tables.add("sessions")
            return
        if sl.startswith("create table if not exists segments"):
            if self.db.dim is None:
                m = _VEC.search(s)
                if m:
                    self.db.dim = int(m.group(1))
            self.db.tables.add("segments")
            return
        if sl.startswith("create table if not exists schema_migrations"):
            self.db.tables.add("schema_migrations")
            return
        if sl.startswith("alter table sessions add column"):
            return  # column appears via dict default ("default")
        if sl.startswith("alter table segments add column"):
            return
        # schema_migrations ------------------------------------------------
        if sl.startswith("select version from schema_migrations"):
            self._rows = [(m["version"],) for m in self.db.schema_migrations]
            return
        if sl.startswith("select max(version) from schema_migrations"):
            versions = [m["version"] for m in self.db.schema_migrations]
            self._rows = [(max(versions) if versions else None,)]
            return
        if sl.startswith("insert into schema_migrations"):
            version, title = params
            if not any(m["version"] == version for m in self.db.schema_migrations):
                self.db.schema_migrations.append(
                    {"version": int(version), "title": title, "applied_at": time.time()}
                )
            return
        # Dim-guard query --------------------------------------------------
        if "from pg_attribute" in sl:
            self._rows = [(f"vector({self.db.dim})",)] if self.db.dim is not None else []
            return
        # Inserts ----------------------------------------------------------
        if sl.startswith("insert into sessions"):
            keys = ["id", "source", "lang", "tenant_id", "created_at"]
            row = dict(zip(keys, params))
            if "on conflict" in sl:
                if any(s["id"] == row["id"] for s in self.db.sessions):
                    return
            self.db.sessions.append({**{"tenant_id": "default"}, **row})
            return
        if sl.startswith("insert into segments"):
            keys = ["id", "session_id", "speaker", "text", "lang", "tenant_id",
                    "start_ms", "end_ms", "created_at", "embedding"]
            row = dict(zip(keys, params))
            row["embedding"] = _parse_vec_str(row["embedding"])
            self.db.segments.append({**{"tenant_id": "default"}, **row})
            return
        # Reads ------------------------------------------------------------
        if sl.startswith("select count(*) from segments where tenant_id"):
            (tid,) = params
            n = sum(1 for s in self.db.segments if s["tenant_id"] == tid)
            self._rows = [(n,)]
            return
        if sl.startswith("select id, source, lang, tenant_id, created_at from sessions"):
            (tid,) = params
            rows = [
                (s["id"], s.get("source"), s.get("lang"), s["tenant_id"], s["created_at"])
                for s in self.db.sessions if s["tenant_id"] == tid
            ]
            rows.sort(key=lambda r: r[4], reverse=True)
            self._rows = rows
            return
        if sl.startswith("select id, session_id, speaker, text, lang, tenant_id, start_ms, end_ms, created_at from segments"):
            (tid,) = params
            self._rows = [
                (s["id"], s["session_id"], s.get("speaker"), s["text"], s.get("lang"),
                 s["tenant_id"], s.get("start_ms", 0), s.get("end_ms", 0), s["created_at"])
                for s in self.db.segments if s["tenant_id"] == tid
            ]
            return
        if sl.startswith("select id, session_id, speaker, text, lang, tenant_id, start_ms, end_ms, created_at, 1 - (embedding <=> %s) as score from segments"):
            # The big search query. Params shape:
            #   [query_vec, tenant_id, *extra_filter_values, query_vec, top_k]
            # `where` is built by PgVectorStore.search in this order:
            #   tenant_id (always), lang?, session_id?, since?, until?
            qv = _parse_vec_str(params[0])
            top_k = int(params[-1])
            # Walk the SQL WHERE clause to know which filters are present.
            tenant_id = params[1]
            i = 2
            lang = session_id = since = until = None
            if " lang = %s" in sl:
                lang = params[i]; i += 1
            if " session_id = %s" in sl:
                session_id = params[i]; i += 1
            if " created_at >= %s" in sl:
                since = float(params[i]); i += 1
            if " created_at <= %s" in sl:
                until = float(params[i]); i += 1
            candidates = [s for s in self.db.segments if s["tenant_id"] == tenant_id]
            if lang is not None:
                candidates = [s for s in candidates if s.get("lang") == lang]
            if session_id is not None:
                candidates = [s for s in candidates if s.get("session_id") == session_id]
            if since is not None:
                candidates = [s for s in candidates if s["created_at"] >= since]
            if until is not None:
                candidates = [s for s in candidates if s["created_at"] <= until]
            scored = [(s, _cosine(qv, s["embedding"])) for s in candidates]
            scored.sort(key=lambda p: p[1], reverse=True)
            rows = []
            for s, score in scored[:top_k]:
                rows.append((
                    s["id"], s["session_id"], s.get("speaker"), s["text"], s.get("lang"),
                    s["tenant_id"], s.get("start_ms", 0), s.get("end_ms", 0),
                    s["created_at"], float(score),
                ))
            self._rows = rows
            return
        # Deletes ---------------------------------------------------------
        if sl.startswith("delete from segments where tenant_id"):
            (tid,) = params
            before = len(self.db.segments)
            self.db.segments = [s for s in self.db.segments if s["tenant_id"] != tid]
            self.rowcount = before - len(self.db.segments)
            return
        if sl.startswith("delete from sessions where tenant_id"):
            (tid,) = params
            before = len(self.db.sessions)
            self.db.sessions = [s for s in self.db.sessions if s["tenant_id"] != tid]
            self.rowcount = before - len(self.db.sessions)
            return
        if sl.startswith("delete from segments where session_id"):
            sid, tid = params
            before = len(self.db.segments)
            self.db.segments = [
                s for s in self.db.segments
                if not (s["session_id"] == sid and s["tenant_id"] == tid)
            ]
            self.rowcount = before - len(self.db.segments)
            return
        if sl.startswith("delete from sessions where id"):
            sid, tid = params
            before = len(self.db.sessions)
            self.db.sessions = [
                s for s in self.db.sessions
                if not (s["id"] == sid and s["tenant_id"] == tid)
            ]
            self.rowcount = before - len(self.db.sessions)
            return
        raise NotImplementedError(f"fake_psycopg got unexpected SQL: {sql!r}")

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)
