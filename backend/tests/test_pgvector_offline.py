"""Offline pgvector store test — uses the in-memory psycopg fake so we get fast
feedback on the store's SQL shape + migrations + dim guard without needing Docker.

Real-Postgres semantics still belong to tests/test_pgvector.py (skipped without
TEST_DATABASE_URL); this file is the safety net for the long-tail of refactors that
touch the SQL strings."""
from __future__ import annotations

import pytest

from app.domain import Segment, Session
from app.store.pgvector import DimMismatchError, PgVectorStore
from tests.fakes import fake_psycopg as fake


@pytest.fixture(autouse=True)
def reset_fake():
    fake.reset()
    yield
    fake.reset()


def _store(dsn: str = "fake://db", dim: int = 4) -> PgVectorStore:
    return PgVectorStore(dsn, dim, connect=fake.connect)


def test_migrations_apply_v1_and_v2_on_first_init():
    s = _store()
    assert s.applied == [1, 2]
    db = fake._REGISTRY["fake://db"]
    assert {m["version"] for m in db.schema_migrations} == {1, 2}


def test_migrations_are_idempotent():
    _store()  # first init applies v1+v2
    # Re-open the same DSN. State is reused → applied should be []
    s2 = _store()
    assert s2.applied == []


def test_roundtrip_search_with_tenant_filter():
    store = _store(dim=4)
    sess = Session(lang="en", tenant_id="alice")
    store.add_session(sess)
    store.add_segments([
        Segment(text="ship the demo on Friday", session_id=sess.id,
                tenant_id="alice", lang="en", embedding=[1, 0, 0, 0]),
        Segment(text="decide the price later", session_id=sess.id,
                tenant_id="alice", lang="en", embedding=[0, 1, 0, 0]),
    ])
    hits = store.search([1, 0, 0, 0], top_k=2, tenant_id="alice")
    assert hits[0][0].text == "ship the demo on Friday"
    # tenant=bob sees nothing.
    assert store.search([1, 0, 0, 0], top_k=5, tenant_id="bob") == []


def test_combined_filters_lang_session_time():
    store = _store(dim=3)
    s_en = Session(lang="en", tenant_id="t1")
    s_uz = Session(lang="uz", tenant_id="t1")
    store.add_session(s_en); store.add_session(s_uz)
    store.add_segments([
        Segment(text="en1", session_id=s_en.id, tenant_id="t1", lang="en",
                embedding=[1, 0, 0], created_at=1000.0),
        Segment(text="uz1", session_id=s_uz.id, tenant_id="t1", lang="uz",
                embedding=[1, 0, 0], created_at=2000.0),
        Segment(text="uz2", session_id=s_uz.id, tenant_id="t1", lang="uz",
                embedding=[1, 0, 0], created_at=3000.0),
    ])
    # lang=uz + session=s_uz + window 1500..2500 → only uz1.
    hits = store.search([1, 0, 0], top_k=5, tenant_id="t1",
                        lang="uz", session_id=s_uz.id,
                        since=1500.0, until=2500.0)
    assert [h[0].text for h in hits] == ["uz1"]


def test_delete_session_does_not_cross_tenants():
    store = _store(dim=3)
    a = Session(lang="en", tenant_id="alice"); b = Session(lang="en", tenant_id="bob")
    store.add_session(a); store.add_session(b)
    store.add_segments([
        Segment(text="alice's", session_id=a.id, tenant_id="alice", lang="en",
                embedding=[1, 0, 0]),
        Segment(text="bob's",   session_id=b.id, tenant_id="bob",   lang="en",
                embedding=[1, 0, 0]),
    ])
    # Bob tries to delete alice's session id under his own tenant — no-op.
    assert store.delete_session(a.id, "bob") == 0
    assert len(store.all_segments("alice")) == 1
    # Real owner can delete.
    assert store.delete_session(a.id, "alice") == 1
    assert store.all_segments("alice") == []


def test_dim_mismatch_raises_on_reopen():
    fake.attach("fake://dim", fake.Database())
    PgVectorStore("fake://dim", dim=4, connect=fake.connect)
    with pytest.raises(DimMismatchError):
        PgVectorStore("fake://dim", dim=8, connect=fake.connect)


def test_delete_all_scoped_to_caller():
    store = _store(dim=3)
    a = Session(lang="en", tenant_id="alice"); b = Session(lang="en", tenant_id="bob")
    store.add_session(a); store.add_session(b)
    store.add_segments([
        Segment(text="A", session_id=a.id, tenant_id="alice", lang="en", embedding=[1, 0, 0]),
        Segment(text="B", session_id=b.id, tenant_id="bob",   lang="en", embedding=[1, 0, 0]),
    ])
    assert store.delete_all("alice") == 1
    assert store.all_segments("alice") == []
    assert len(store.all_segments("bob")) == 1
