"""Diarization + owner-enrollment tests. Runs fully offline with the mock diarizer.

The pyannote backend is import-tested only (HF is blocked in this sandbox; real e2e is
the team's job in the in-country env).
"""
from __future__ import annotations

import math

import pytest


# ---- MockDiarizer --------------------------------------------------------
def test_mock_diarizer_alternates_speakers():
    from app.providers.mock import MockDiarizer

    d = MockDiarizer()
    turns = d.diarize(b"hello from owner\nresponse from other\nowner again")
    assert [t["speaker_label"] for t in turns] == ["SPEAKER_00", "SPEAKER_01", "SPEAKER_00"]
    # Each turn carries a voiceprint of the configured dim.
    assert all(len(t["voiceprint"]) == d.dim for t in turns)
    # Same-speaker turns share an identical voiceprint (key property for owner matching).
    assert turns[0]["voiceprint"] == turns[2]["voiceprint"]
    assert turns[0]["voiceprint"] != turns[1]["voiceprint"]


def test_mock_diarizer_embed_voice_matches_first_line_of_same_speaker():
    """Enrolling with a clip whose first line equals SPEAKER_00's first turn in a meeting
    must produce the SAME voiceprint as that speaker's turn — that is what makes the
    owner-mapping end-to-end testable."""
    from app.providers.mock import MockDiarizer

    d = MockDiarizer()
    meeting = b"Salom, men Asrbek\nHi I am the other person\nyana asrbek gapiryapti"
    enrollment = b"Salom, men Asrbek"
    turns = d.diarize(meeting)
    owner_voice = d.embed_voice(enrollment)
    speaker_00_voice = next(t["voiceprint"] for t in turns if t["speaker_label"] == "SPEAKER_00")
    assert owner_voice == speaker_00_voice


def test_mock_diarizer_empty_audio_returns_no_turns():
    from app.providers.mock import MockDiarizer
    assert MockDiarizer().diarize(b"") == []


# ---- OwnerEnrollment -----------------------------------------------------
def test_owner_enrollment_matches_self_and_rejects_unrelated():
    from app.owner import OwnerEnrollment
    from app.providers.mock import MockDiarizer

    d = MockDiarizer()
    e = OwnerEnrollment(path=None, threshold=0.7)
    assert not e.enrolled

    e.enroll([d.embed_voice(b"Salom, men Asrbek")])
    assert e.enrolled
    assert e.status()["samples"] == 1

    same = d.embed_voice(b"Salom, men Asrbek")
    other = d.embed_voice(b"completely different person speaking")
    assert e.is_owner(same)
    assert not e.is_owner(other)
    # Score for self should be ~1.0 (unit-norm vectors, identical seed).
    assert math.isclose(e.score(same), 1.0, rel_tol=1e-6)


def test_owner_enrollment_persists_to_file(tmp_path):
    """Restarts of the server must not lose the enrollment — that would make every
    Omnisense user re-enroll after a kernel update."""
    from app.owner import OwnerEnrollment
    from app.providers.mock import MockDiarizer

    path = tmp_path / "owner.json"
    voice = MockDiarizer().embed_voice(b"reference clip")

    a = OwnerEnrollment(path=str(path), threshold=0.5)
    a.enroll([voice])
    assert path.is_file()

    b = OwnerEnrollment(path=str(path), threshold=0.5)
    assert b.enrolled
    assert b.is_owner(voice)


def test_owner_clear_removes_file(tmp_path):
    from app.owner import OwnerEnrollment
    from app.providers.mock import MockDiarizer

    path = tmp_path / "owner.json"
    OwnerEnrollment(path=str(path)).enroll([MockDiarizer().embed_voice(b"me")])
    assert path.is_file()
    e = OwnerEnrollment(path=str(path))
    e.clear()
    assert not e.enrolled
    assert not path.is_file()


def test_owner_enroll_requires_non_empty_voiceprint():
    from app.owner import OwnerEnrollment
    with pytest.raises(ValueError):
        OwnerEnrollment().enroll([])


# ---- Pipeline integration -----------------------------------------------
def test_pipeline_applies_owner_label_after_enrollment(tmp_path):
    """End-to-end: diarizer on, owner enrolled with the SPEAKER_00 reference — incoming
    SPEAKER_00 turns must come out tagged 'owner' instead of 'SPEAKER_00'."""
    from app.config import Settings
    from app.pipeline import Pipeline

    s = Settings(
        diarizer_provider="mock",
        owner_voiceprint_path=str(tmp_path / "owner.json"),
        owner_match_threshold=0.7,
    )
    p = Pipeline(s)
    p.delete_all()

    # Enroll with the first speaker's opening line.
    voice = p.diarizer.embed_voice(b"Bugun mijoz bilan demo haqida gaplashdik.")
    p.owner.enroll([voice])

    # Ingest a "meeting" — MockSTT line-splits, MockDiarizer alternates SPEAKER_00/01.
    transcript = (
        "Bugun mijoz bilan demo haqida gaplashdik.\n"
        "We agreed to deliver the first demo by Friday.\n"
        "Narxni keyinroq hal qilamiz."
    )
    p.ingest_audio(transcript.encode("utf-8"), lang="uz")
    speakers = [s.speaker for s in p.store.all_segments()]
    assert "owner" in speakers
    assert speakers.count("owner") == 2          # lines 1 and 3 are SPEAKER_00 → owner
    assert all(s != "SPEAKER_00" for s in speakers)  # raw label was replaced


def test_pipeline_default_off_preserves_stt_speakers():
    """When OMNI_DIARIZER=off (default), STT's own speaker labels must come through —
    keeps the pre-task-2 demo behavior untouched."""
    from app.config import Settings
    from app.pipeline import Pipeline

    p = Pipeline(Settings(diarizer_provider="off"))
    p.delete_all()
    p.ingest_audio(b"line one\nline two", lang="en")
    speakers = {s.speaker for s in p.store.all_segments()}
    # MockSTT labels alternate owner / speaker_2.
    assert speakers == {"owner", "speaker_2"}


def test_pipeline_diarizer_no_owner_uses_other_label():
    from app.config import Settings
    from app.pipeline import Pipeline

    p = Pipeline(Settings(diarizer_provider="mock"))
    p.delete_all()
    p.ingest_audio(b"line one\nline two", lang="en")
    speakers = {s.speaker for s in p.store.all_segments()}
    # With diarization on but no enrollment: labels become other / other_1 (no "owner").
    assert "owner" not in speakers
    assert any(s.startswith("other") for s in speakers)


# ---- Pyannote backend ---------------------------------------------------
def test_pyannote_requires_hf_token(monkeypatch):
    """Import-test only — pyannote weights are gated and HF is blocked here. We just
    verify the adapter raises a clean, actionable error when HF_TOKEN is missing."""
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("HUGGING_FACE_HUB_TOKEN", raising=False)
    from app.providers.diarize_pyannote import PyannoteDiarizer
    with pytest.raises(ValueError, match="HF_TOKEN"):
        PyannoteDiarizer(hf_token=None)


# ---- API endpoints ------------------------------------------------------
def test_enroll_endpoint_rejects_when_diarizer_off(monkeypatch):
    """The endpoint must refuse if no diarizer is configured — otherwise the user gets a
    confusingly-enrolled state that nothing can match against."""
    from fastapi.testclient import TestClient

    import app.main as main_mod
    from app.config import Settings
    from app.pipeline import Pipeline

    monkeypatch.setattr(main_mod, "pipeline", Pipeline(Settings(diarizer_provider="off")))
    client = TestClient(main_mod.app)

    r = client.post("/enroll/owner", files={"file": ("ref.wav", b"hi", "audio/wav")})
    assert r.status_code == 400
    assert "diarizer" in r.json()["detail"].lower()


def test_enroll_endpoint_round_trip(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    import app.main as main_mod
    from app.config import Settings
    from app.pipeline import Pipeline

    s = Settings(
        diarizer_provider="mock",
        owner_voiceprint_path=str(tmp_path / "owner.json"),
    )
    monkeypatch.setattr(main_mod, "pipeline", Pipeline(s))
    client = TestClient(main_mod.app)

    # Status before enrollment
    r = client.get("/enroll/owner")
    assert r.status_code == 200
    assert r.json()["enrolled"] is False

    # Enroll
    r = client.post("/enroll/owner", files={"file": ("ref.wav", b"hi i am owner", "audio/wav")})
    assert r.status_code == 200
    body = r.json()
    assert body["enrolled"] is True
    assert body["samples"] == 1

    # Clear
    r = client.delete("/enroll/owner")
    assert r.status_code == 200
    assert r.json()["enrolled"] is False
