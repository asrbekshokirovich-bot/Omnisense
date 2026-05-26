"""API-level multi-tenancy + usage-metering tests.

The X-User-Id header is the (Phase-0, thin) tenant identity. Missing → "default". Two
different headers must produce fully isolated memories, sessions, owner enrollments, and
usage counters.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.main as main_mod
from app.config import Settings
from app.pipeline import Pipeline


@pytest.fixture
def client(monkeypatch, tmp_path):
    """Fresh pipeline per test so usage counters & owner enrollments don't bleed across."""
    s = Settings(
        diarizer_provider="mock",
        owner_voiceprint_path=str(tmp_path / "owner.json"),
    )
    monkeypatch.setattr(main_mod, "pipeline", Pipeline(s))
    return TestClient(main_mod.app)


def _ingest(client, text, user):
    return client.post("/ingest/text", json={"text": text, "lang": "en"},
                       headers={"X-User-Id": user})


def test_isolated_ingest_and_recall(client):
    _ingest(client, "alice's plan is to ship Friday", "alice").raise_for_status()
    _ingest(client, "bob's deadline is next Monday",  "bob"  ).raise_for_status()

    a = client.post("/ask", json={"question": "when do we ship?", "lang": "en"},
                    headers={"X-User-Id": "alice"}).json()
    b = client.post("/ask", json={"question": "when do we ship?", "lang": "en"},
                    headers={"X-User-Id": "bob"}).json()

    # Each tenant's top citation comes from their own memory only.
    assert "alice" in a["citations"][0]["text"].lower()
    assert "bob"   in b["citations"][0]["text"].lower()
    assert not any("bob"   in c["text"].lower() for c in a["citations"])
    assert not any("alice" in c["text"].lower() for c in b["citations"])


def test_default_tenant_when_header_missing(client):
    _ingest(client, "no-header note", "")
    r = client.get("/sessions").json()
    assert len(r["sessions"]) == 1


def test_delete_all_only_clears_caller(client):
    _ingest(client, "alice line", "alice")
    _ingest(client, "bob line", "bob")
    r = client.delete("/data", headers={"X-User-Id": "alice"})
    assert r.status_code == 200
    assert client.get("/sessions", headers={"X-User-Id": "alice"}).json()["sessions"] == []
    assert len(client.get("/sessions", headers={"X-User-Id": "bob"}).json()["sessions"]) == 1


def test_session_delete_refuses_wrong_tenant(client):
    """Knowing another user's session_id must not let you delete their memory."""
    sid = _ingest(client, "alice meeting", "alice").json()["session_id"]
    # Bob tries to delete Alice's session_id.
    r = client.delete(f"/sessions/{sid}", headers={"X-User-Id": "bob"}).json()
    assert r["deleted_segments"] == 0
    # Alice's memory is still there.
    assert len(client.get("/sessions", headers={"X-User-Id": "alice"}).json()["sessions"]) == 1


def test_usage_meter_increments_and_isolates(client):
    _ingest(client, "alice line 1", "alice")
    _ingest(client, "alice line 2", "alice")
    client.post("/ask", json={"question": "?", "lang": "en"}, headers={"X-User-Id": "alice"})
    client.get("/briefing", headers={"X-User-Id": "alice"})

    a = client.get("/usage", headers={"X-User-Id": "alice"}).json()
    b = client.get("/usage", headers={"X-User-Id": "bob"}).json()

    assert a["segments_ingested"] == 2
    assert a["questions_asked"] == 1
    assert a["briefings_generated"] == 1
    # Bob has done nothing — but the counter object still initializes lazily.
    assert b["segments_ingested"] == 0
    assert b["questions_asked"] == 0


def test_owner_enrollment_isolated_per_tenant(client):
    """Enrollment is per-tenant — Alice's voiceprint must NOT label Bob's recordings."""
    alice_enroll = client.post(
        "/enroll/owner",
        files={"file": ("ref.wav", b"i am alice and i open meetings", "audio/wav")},
        headers={"X-User-Id": "alice"},
    )
    assert alice_enroll.status_code == 200 and alice_enroll.json()["enrolled"]

    # Bob is not enrolled.
    assert client.get("/enroll/owner", headers={"X-User-Id": "bob"}).json()["enrolled"] is False

    # When Alice's enrollment-line opens a meeting, her SPEAKER_00 becomes "owner".
    files = {"file": ("m.txt", b"i am alice and i open meetings\nresponse from bob", "audio/wav")}
    client.post("/ingest/audio", files=files, data={"lang": "en"},
                headers={"X-User-Id": "alice"})

    speakers = {s.speaker for s in main_mod.pipeline.store.all_segments("alice")}
    assert "owner" in speakers

    # Bob ingests the same audio: no enrollment → no "owner" label.
    client.post("/ingest/audio", files=files, data={"lang": "en"},
                headers={"X-User-Id": "bob"})
    bob_speakers = {s.speaker for s in main_mod.pipeline.store.all_segments("bob")}
    assert "owner" not in bob_speakers


def test_invalid_user_id_rejected(client):
    long_id = "x" * 200
    r = client.post("/ingest/text", json={"text": "hi", "lang": "en"},
                    headers={"X-User-Id": long_id})
    assert r.status_code == 400
