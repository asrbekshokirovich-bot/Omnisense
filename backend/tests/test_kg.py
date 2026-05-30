"""Knowledge-graph memory tests — MockKnowledgeGraph extraction + Pipeline wiring +
the /facts endpoint + the Graphiti/Mem0 fail-loud guards."""
from __future__ import annotations

import pytest


# ---- MockKnowledgeGraph extraction --------------------------------------
def test_extracts_english_action_item():
    from app.kg import MockKnowledgeGraph

    kg = MockKnowledgeGraph()
    facts = kg.extract_facts(
        "I will send the contract tomorrow.",
        segment_id="s1", session_id="m1", tenant_id="t",
    )
    # At least one fact captures the commitment.
    assert any(f.subject == "i" and f.predicate == "will" and "contract" in f.object.lower()
               for f in facts)
    # Temporal tag picked up.
    assert any(f.temporal == "tomorrow" for f in facts)


def test_extracts_russian_decision():
    from app.kg import MockKnowledgeGraph

    kg = MockKnowledgeGraph()
    facts = kg.extract_facts(
        "Мы решили отправить контракт завтра",
        segment_id="s1", session_id="m1", tenant_id="t",
    )
    assert any(f.predicate == "decided" and "контракт" in f.object.lower() for f in facts)
    assert any(f.temporal == "tomorrow" for f in facts)


def test_extracts_uzbek_agreement():
    from app.kg import MockKnowledgeGraph

    kg = MockKnowledgeGraph()
    facts = kg.extract_facts(
        "Biz juma kuni demoni yetkazib berishga kelishdik",
        segment_id="s1", session_id="m1", tenant_id="t",
    )
    assert any(f.predicate == "agreed" for f in facts)
    assert any(f.temporal == "friday" for f in facts)


def test_extraction_is_idempotent_for_same_text():
    """Duplicate inputs (e.g. retried ingest) must not duplicate facts inside a single
    call — within a single segment, repeated patterns dedupe."""
    from app.kg import MockKnowledgeGraph

    kg = MockKnowledgeGraph()
    text = "I will ship the demo. I will ship the demo."
    facts = kg.extract_facts(text, segment_id="s", session_id="m", tenant_id="t")
    # The second "I will ship the demo" is identical (same subject/predicate/object)
    # so it collapses.
    matches = [f for f in facts if "ship the demo" in f.object.lower()]
    assert len(matches) == 1


def test_search_and_list_are_tenant_scoped():
    from app.kg import MockKnowledgeGraph

    kg = MockKnowledgeGraph()
    kg.extract_facts("I will ship Friday",
                     segment_id="s1", session_id="m1", tenant_id="alice")
    kg.extract_facts("Bob will write the contract",
                     segment_id="s2", session_id="m2", tenant_id="bob")

    alice = kg.list_facts(tenant_id="alice")
    assert all(f.tenant_id == "alice" for f in alice)
    assert len(alice) >= 1

    # Search respects tenancy.
    hits = kg.search_facts("contract", tenant_id="alice")
    assert all("contract" not in f.object.lower() or f.tenant_id == "alice" for f in hits)
    assert hits == []  # alice has no contract facts
    bob_hits = kg.search_facts("contract", tenant_id="bob")
    assert any("contract" in f.object.lower() for f in bob_hits)


def test_delete_session_does_not_cross_tenants():
    from app.kg import MockKnowledgeGraph

    kg = MockKnowledgeGraph()
    kg.extract_facts("I will deliver", segment_id="s", session_id="alice-meeting",
                     tenant_id="alice")
    kg.extract_facts("I will deliver", segment_id="s", session_id="alice-meeting",
                     tenant_id="bob")
    # Bob tries to delete alice's session id under his own tenant — only his own goes.
    assert kg.delete_session("alice-meeting", tenant_id="bob") >= 1
    assert kg.list_facts(tenant_id="alice")  # alice's still there


def test_delete_all_scoped_to_caller():
    from app.kg import MockKnowledgeGraph

    kg = MockKnowledgeGraph()
    kg.extract_facts("I will A", segment_id="s", session_id="m", tenant_id="alice")
    kg.extract_facts("I will B", segment_id="s", session_id="m", tenant_id="bob")
    assert kg.delete_all(tenant_id="alice") >= 1
    assert kg.list_facts(tenant_id="alice") == []
    assert kg.list_facts(tenant_id="bob") != []


# ---- Pipeline integration ------------------------------------------------
def test_pipeline_populates_kg_on_ingest_when_configured():
    from app.config import Settings
    from app.pipeline import Pipeline

    p = Pipeline(Settings(kg_provider="mock"))
    p.delete_all()
    p.ingest_text("We agreed to ship the demo on Friday.", lang="en")

    facts = p.kg.list_facts(tenant_id="default")
    assert any(f.predicate == "agreed" for f in facts)


def test_pipeline_skips_kg_when_off():
    """Default OMNI_KG=off must keep the pipeline at the pre-task-8 behavior. The
    offline demo never touches a KG."""
    from app.config import Settings
    from app.pipeline import Pipeline

    p = Pipeline(Settings())  # kg_provider defaults to "off"
    assert p.kg is None
    # Ingest still works without a KG.
    p.delete_all()
    p.ingest_text("hello", lang="en")


def test_pipeline_delete_session_clears_kg():
    from app.config import Settings
    from app.pipeline import Pipeline

    p = Pipeline(Settings(kg_provider="mock"))
    p.delete_all()
    sess = p.ingest_text("I will deliver tomorrow", lang="en")
    assert p.kg.list_facts(tenant_id="default")
    p.delete_session(sess.id)
    assert p.kg.list_facts(tenant_id="default") == []


# ---- API endpoint ------------------------------------------------------
def test_facts_endpoint(monkeypatch):
    from fastapi.testclient import TestClient

    import app.main as main_mod
    from app.config import Settings
    from app.pipeline import Pipeline

    monkeypatch.setattr(main_mod, "pipeline",
                        Pipeline(Settings(kg_provider="mock",
                                          rate_per_min=600, rate_burst=100)))
    client = TestClient(main_mod.app)
    h = {"X-User-Id": "alice"}

    client.post("/ingest/text",
                json={"text": "We agreed to ship the demo on Friday.", "lang": "en"},
                headers=h).raise_for_status()
    # No query → list facts.
    r = client.get("/facts", headers=h).json()
    assert r["provider"] == "mock"
    assert r["facts"]
    # Query narrows.
    r = client.get("/facts?q=Friday", headers=h).json()
    assert any(f["temporal"] == "friday" for f in r["facts"])


def test_facts_endpoint_returns_empty_when_kg_off(monkeypatch):
    from fastapi.testclient import TestClient

    import app.main as main_mod
    from app.config import Settings
    from app.pipeline import Pipeline

    monkeypatch.setattr(main_mod, "pipeline", Pipeline(Settings()))
    client = TestClient(main_mod.app)
    r = client.get("/facts").json()
    assert r == {"provider": "off", "facts": []}


# ---- Stub adapters fail loud --------------------------------------------
def test_graphiti_stub_raises():
    from app.kg import make_kg
    with pytest.raises(NotImplementedError):
        make_kg("graphiti")


def test_mem0_stub_raises():
    from app.kg import make_kg
    with pytest.raises(NotImplementedError):
        make_kg("mem0")
