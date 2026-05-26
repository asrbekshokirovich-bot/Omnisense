"""Integration test for the pgvector store. Skips unless a reachable Postgres+pgvector is
configured via TEST_DATABASE_URL (e.g. the infra/docker-compose stack). Run by the team in
an environment with Docker; the offline suite covers the in-memory store."""
import os

import pytest

psycopg = pytest.importorskip("psycopg")

DSN = os.environ.get("TEST_DATABASE_URL")
if not DSN:
    pytest.skip("set TEST_DATABASE_URL to run the pgvector integration test", allow_module_level=True)


def test_pgvector_roundtrip():
    from app.domain import Segment, Session
    from app.store.pgvector import PgVectorStore

    store = PgVectorStore(DSN, dim=4)
    store.delete_all()

    session = Session(lang="en")
    store.add_session(session)
    store.add_segments([
        Segment(text="ship the demo on friday", session_id=session.id, embedding=[1, 0, 0, 0]),
        Segment(text="decide the price later", session_id=session.id, embedding=[0, 1, 0, 0]),
    ])

    hits = store.search([1, 0, 0, 0], top_k=1)
    assert hits and "demo" in hits[0][0].text
    assert store.delete_all() >= 2
