"""Consent log + region gating tests."""
from __future__ import annotations

import pytest


# ---- ConsentLog ---------------------------------------------------------
def test_consent_log_latest_wins(tmp_path):
    from app.consent import ConsentLog

    log = ConsentLog(path=str(tmp_path / "c.json"))
    assert log.is_granted("cross_border_llm") is False  # fail-closed default

    log.record("cross_border_llm", True, reason="user accepted on first launch")
    assert log.is_granted("cross_border_llm")

    log.record("cross_border_llm", False, reason="changed mind")
    assert log.is_granted("cross_border_llm") is False

    # The audit trail keeps BOTH entries.
    status = log.status()
    assert len(status["log"]) == 2
    assert status["current"]["cross_border_llm"]["granted"] is False


def test_consent_log_persists_across_instances(tmp_path):
    """Restarts must not lose grants — otherwise every consent prompt becomes a
    privacy regression."""
    from app.consent import ConsentLog

    path = str(tmp_path / "c.json")
    ConsentLog(path=path).record("recording", True)

    fresh = ConsentLog(path=path)
    assert fresh.is_granted("recording")
    assert len(fresh.status()["log"]) == 1


def test_consent_log_rejects_empty_scope():
    from app.consent import ConsentLog
    with pytest.raises(ValueError):
        ConsentLog().record("", True)


def test_consent_log_handles_corrupt_file(tmp_path):
    path = tmp_path / "c.json"
    path.write_text("not json", encoding="utf-8")
    from app.consent import ConsentLog
    log = ConsentLog(path=str(path))
    assert log.status()["log"] == []
    # Re-grant works after corruption — append, don't crash.
    log.record("recording", True)
    assert log.is_granted("recording")


# ---- Pipeline region gate -----------------------------------------------
def test_pipeline_mock_llm_never_requires_consent(tmp_path):
    """Default OMNI_LLM=mock is in-process — must not require consent or we break the
    offline demo + 48-test suite."""
    from app.config import Settings
    from app.pipeline import Pipeline

    p = Pipeline(Settings(llm_provider="mock"))
    p.delete_all()
    p.ingest_text("hello", lang="en")
    out = p.ask("?", lang="en")
    assert "answer" in out


def test_pipeline_blocks_cross_border_llm_without_consent(tmp_path):
    from app.config import Settings
    from app.pipeline import ConsentRequired, Pipeline

    p = Pipeline(Settings(
        llm_provider="anthropic",
        anthropic_api_key="sk-fake",  # only needed for the adapter to instantiate
        consent_log_path=str(tmp_path / "consent.json"),
    ))
    p.delete_all()
    p.ingest_text("hello", lang="en")
    with pytest.raises(ConsentRequired) as exc:
        p.ask("?", lang="en")
    assert exc.value.scope == "cross_border_llm"
    assert exc.value.provider == "anthropic"


def test_pipeline_allows_after_consent_grant(tmp_path, monkeypatch):
    """With consent on file, the cross-border LLM call must go through. We stub the
    Anthropic HTTP layer so the test does not hit the network."""
    from app.config import Settings
    from app.pipeline import Pipeline

    p = Pipeline(Settings(
        llm_provider="anthropic",
        anthropic_api_key="sk-fake",
        consent_log_path=str(tmp_path / "consent.json"),
    ))
    p.delete_all()
    p.consent().record("cross_border_llm", True)

    # Patch the AnthropicLLM's _message so we do not actually hit the network.
    monkeypatch.setattr(p.llm, "_message",
                        lambda *a, **kw: "OK — consent recorded; demo went through.")
    p.ingest_text("ship the demo on Friday", lang="en")
    out = p.ask("when?", lang="en")
    assert "OK" in out["answer"]


def test_pipeline_blocks_cross_border_stt_without_consent(tmp_path, monkeypatch):
    """Yandex STT is cross-border — ingest_audio must refuse without consent."""
    from app.config import Settings
    from app.pipeline import ConsentRequired, Pipeline

    p = Pipeline(Settings(
        stt_provider="yandex",
        yandex_api_key="key",
        yandex_folder_id="folder",
        consent_log_path=str(tmp_path / "consent.json"),
    ))
    p.delete_all()
    with pytest.raises(ConsentRequired) as exc:
        p.ingest_audio(b"x" * 100, lang="ru")
    assert exc.value.scope == "cross_border_stt"


# ---- API ---------------------------------------------------------------
def test_consent_endpoints_round_trip(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    import app.main as main_mod
    from app.config import Settings
    from app.pipeline import Pipeline

    s = Settings(consent_log_path=str(tmp_path / "c.json"))
    monkeypatch.setattr(main_mod, "pipeline", Pipeline(s))
    client = TestClient(main_mod.app)

    # Nothing granted yet.
    r = client.get("/consent", headers={"X-User-Id": "alice"})
    assert r.json()["current"] == {}

    # Grant.
    r = client.post("/consent/cross_border_llm",
                    json={"granted": True, "reason": "first launch"},
                    headers={"X-User-Id": "alice"})
    assert r.status_code == 200
    entry = r.json()
    assert entry["scope"] == "cross_border_llm" and entry["granted"] is True

    # Revoke — both entries appear in the audit log.
    client.post("/consent/cross_border_llm",
                json={"granted": False, "reason": "changed mind"},
                headers={"X-User-Id": "alice"})
    status = client.get("/consent", headers={"X-User-Id": "alice"}).json()
    assert len(status["log"]) == 2
    assert status["current"]["cross_border_llm"]["granted"] is False


def test_api_returns_451_when_consent_missing(monkeypatch, tmp_path):
    """A cross-border LLM call without consent must surface as HTTP 451 with the
    actionable scope/provider info so the client knows what to ask the user."""
    from fastapi.testclient import TestClient

    import app.main as main_mod
    from app.config import Settings
    from app.pipeline import Pipeline

    s = Settings(
        llm_provider="anthropic",
        anthropic_api_key="sk-fake",
        consent_log_path=str(tmp_path / "c.json"),
    )
    monkeypatch.setattr(main_mod, "pipeline", Pipeline(s))
    client = TestClient(main_mod.app)
    # Ingest works (text path doesn't hit a cross-border LLM).
    client.post("/ingest/text", json={"text": "hi", "lang": "en"},
                headers={"X-User-Id": "alice"})

    r = client.post("/ask", json={"question": "?", "lang": "en"},
                    headers={"X-User-Id": "alice"})
    assert r.status_code == 451
    body = r.json()
    assert body["error"] == "consent_required"
    assert body["scope"] == "cross_border_llm"
    assert body["provider"] == "anthropic"


def test_consent_log_isolated_per_tenant(monkeypatch, tmp_path):
    """alice granting cross_border_llm must NOT grant it for bob."""
    from fastapi.testclient import TestClient

    import app.main as main_mod
    from app.config import Settings
    from app.pipeline import Pipeline

    monkeypatch.setattr(main_mod, "pipeline",
                        Pipeline(Settings(consent_log_path=str(tmp_path / "c.json"))))
    client = TestClient(main_mod.app)

    client.post("/consent/cross_border_llm", json={"granted": True},
                headers={"X-User-Id": "alice"})

    alice = client.get("/consent", headers={"X-User-Id": "alice"}).json()
    bob = client.get("/consent", headers={"X-User-Id": "bob"}).json()
    assert alice["current"]["cross_border_llm"]["granted"] is True
    assert bob["current"] == {}
