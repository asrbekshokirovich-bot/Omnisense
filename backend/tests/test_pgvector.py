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
        Segment(text="ship the demo on friday", session_id=session.id, embedding=[1, 0, 0, 0], lang="en"),
        Segment(text="decide the price later", session_id=session.id, embedding=[0, 1, 0, 0], lang="en"),
    ])

    hits = store.search([1, 0, 0, 0], top_k=1)
    assert hits and "demo" in hits[0][0].text
    assert store.delete_all() >= 2


def test_pgvector_search_filters_and_session_delete():
    from app.domain import Segment, Session
    from app.store.pgvector import PgVectorStore

    store = PgVectorStore(DSN, dim=4)
    store.delete_all()

    a = Session(lang="en"); b = Session(lang="uz")
    store.add_session(a); store.add_session(b)
    store.add_segments([
        Segment(text="meeting A line 1", session_id=a.id, lang="en", embedding=[1, 0, 0, 0]),
        Segment(text="meeting A line 2", session_id=a.id, lang="en", embedding=[1, 0, 0, 0]),
        Segment(text="uchrashuv B",      session_id=b.id, lang="uz", embedding=[1, 0, 0, 0]),
    ])

    only_a = store.search([1, 0, 0, 0], top_k=10, session_id=a.id)
    assert len(only_a) == 2
    only_uz = store.search([1, 0, 0, 0], top_k=10, lang="uz")
    assert {h[0].lang for h in only_uz} == {"uz"}

    removed = store.delete_session(a.id)
    assert removed == 2
    leftover = store.search([1, 0, 0, 0], top_k=10)
    assert {h[0].session_id for h in leftover} == {b.id}
    store.delete_all()


def test_pgvector_dim_mismatch_raises():
    """If the team accidentally changes the embedder dim between runs, fail loudly with
    an actionable error — not silent garbage search."""
    import pytest

    from app.store.pgvector import DimMismatchError, PgVectorStore

    # Create at dim=4 …
    PgVectorStore(DSN, dim=4).delete_all()
    # … then reopen at dim=8.
    with pytest.raises(DimMismatchError):
        PgVectorStore(DSN, dim=8)
