"""In-memory store: covers the search filters, per-session delete, and tenant isolation.

The pgvector store implements the same contract; tests/test_pgvector.py exercises it
against the docker-compose stack (skipped unless TEST_DATABASE_URL is set).
"""
from __future__ import annotations

import time

from app.domain import Segment, Session
from app.store.memory import InMemoryStore

T = "default"


def _seg(text: str, sid: str, *, lang: str = "en", t: float | None = None,
         tenant_id: str = T) -> Segment:
    return Segment(
        text=text, session_id=sid, lang=lang, tenant_id=tenant_id,
        embedding=[1.0, 0.0, 0.0],
        created_at=t if t is not None else time.time(),
    )


def test_search_session_id_filter():
    store = InMemoryStore()
    a = Session(); b = Session()
    store.add_session(a); store.add_session(b)
    store.add_segments([
        _seg("from session A", a.id),
        _seg("from session B", b.id),
    ])
    hits = store.search([1.0, 0.0, 0.0], top_k=5, tenant_id=T, session_id=a.id)
    assert len(hits) == 1
    assert "session A" in hits[0][0].text


def test_search_lang_filter():
    store = InMemoryStore()
    s = Session(); store.add_session(s)
    store.add_segments([
        _seg("uzbek line", s.id, lang="uz"),
        _seg("russian line", s.id, lang="ru"),
        _seg("english line", s.id, lang="en"),
    ])
    hits = store.search([1.0, 0.0, 0.0], top_k=5, tenant_id=T, lang="uz")
    assert {h[0].lang for h in hits} == {"uz"}


def test_search_time_window():
    store = InMemoryStore()
    s = Session(); store.add_session(s)
    store.add_segments([
        _seg("old", s.id, t=1000.0),
        _seg("recent", s.id, t=2000.0),
        _seg("newest", s.id, t=3000.0),
    ])
    hits = store.search([1.0, 0.0, 0.0], top_k=5, tenant_id=T, since=1500.0, until=2500.0)
    assert [h[0].text for h in hits] == ["recent"]


def test_delete_session_removes_only_that_session():
    store = InMemoryStore()
    a = Session(); b = Session()
    store.add_session(a); store.add_session(b)
    store.add_segments([_seg("A1", a.id), _seg("A2", a.id), _seg("B1", b.id)])

    removed = store.delete_session(a.id, T)
    assert removed == 2
    remaining = store.all_segments(T)
    assert len(remaining) == 1
    assert remaining[0].text == "B1"
    # Unknown id → no-op, no error.
    assert store.delete_session("does-not-exist", T) == 0


def test_tenant_isolation_search_and_delete():
    """Two tenants ingest into the same store. Each only sees their own; deleting one
    leaves the other untouched. This is the load-bearing invariant for multi-tenancy."""
    store = InMemoryStore()
    s_a = Session(tenant_id="alice")
    s_b = Session(tenant_id="bob")
    store.add_session(s_a); store.add_session(s_b)
    store.add_segments([
        _seg("alice's note", s_a.id, tenant_id="alice"),
        _seg("bob's note",   s_b.id, tenant_id="bob"),
        _seg("alice again",  s_a.id, tenant_id="alice"),
    ])

    alice_hits = store.search([1, 0, 0], top_k=10, tenant_id="alice")
    assert {h[0].text for h in alice_hits} == {"alice's note", "alice again"}
    bob_hits = store.search([1, 0, 0], top_k=10, tenant_id="bob")
    assert {h[0].text for h in bob_hits} == {"bob's note"}

    # delete_session with the wrong tenant must not cross-delete.
    assert store.delete_session(s_a.id, "bob") == 0
    assert len(store.all_segments("alice")) == 2

    # delete_all is tenant-scoped.
    assert store.delete_all("alice") == 2
    assert store.all_segments("alice") == []
    assert len(store.all_segments("bob")) == 1


def test_pipeline_session_filter_routes_through_store(monkeypatch):
    """`/ask`'s session_id arg must reach the store's search filter — easy to regress
    when refactoring keyword args; pin it here."""
    from app.config import Settings
    from app.pipeline import Pipeline

    p = Pipeline(Settings())
    p.delete_all()
    p.ingest_text("ship the demo on friday", lang="en")
    p.ingest_text("price decided later", lang="en")
    sessions = p.store.list_sessions(T)
    assert len(sessions) == 2
    target = sessions[0]

    seen: dict = {}
    real_search = p.store.search

    def spy(*args, **kwargs):
        seen.update(kwargs)
        return real_search(*args, **kwargs)

    monkeypatch.setattr(p.store, "search", spy)
    p.ask("what?", session_id=target.id)
    assert seen.get("session_id") == target.id
    assert seen.get("tenant_id") == "default"
