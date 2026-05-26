"""Core loop tests — run fully offline (mock providers + in-memory store), no infra needed."""
from app.pipeline import Pipeline


def _fresh() -> Pipeline:
    p = Pipeline()
    p.delete_all()
    return p


def test_ingest_and_recall_with_citation():
    p = _fresh()
    p.ingest_text("We agreed to ship the demo on Friday.", lang="en")
    p.ingest_text("We will decide the price of the device later.", lang="en")

    assert p.stats()["segments"] == 2

    result = p.ask("when do we ship the demo?", lang="en")
    assert result["answer"]
    assert result["citations"], "expected at least one cited memory"
    # The Friday segment shares the most tokens with the question, so it should rank first.
    assert "Friday" in result["citations"][0]["text"]
    assert "timestamp" in result["citations"][0]


def test_briefing_extracts_action_items():
    p = _fresh()
    p.ingest_text("We will send the contract tomorrow. Nice weather today.", lang="en")
    brief = p.briefing(lang="en")
    assert brief["segments_count"] >= 1
    assert any("contract" in item.lower() for item in brief["action_items"])


def test_delete_is_total():
    p = _fresh()
    p.ingest_text("Some memory.", lang="en")
    assert p.stats()["segments"] >= 1
    removed = p.delete_all()
    assert removed >= 1
    assert p.stats()["segments"] == 0


def test_uzbek_roundtrip():
    p = _fresh()
    p.ingest_text("Biz juma kuni demoni yetkazib berishga kelishdik.", lang="uz")
    res = p.ask("demo haqida nima dedik?", lang="uz")
    assert res["citations"]
    assert "demo" in res["citations"][0]["text"].lower()
