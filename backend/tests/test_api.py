"""API tests via FastAPI's TestClient — exercises the HTTP loop end to end (offline)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def setup_function():
    client.delete("/data")  # isolate each test from shared in-memory state


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ingest_ask_flow():
    r = client.post("/ingest/text", json={"text": "We agreed to ship the demo on Friday.", "lang": "en"})
    assert r.status_code == 200
    assert r.json()["segments"] >= 1

    r = client.post("/ask", json={"question": "when is the demo?", "lang": "en"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"]
    assert body["citations"]


def test_ingest_audio_as_text_file():
    # MockSTT treats an uploaded file as a UTF-8 transcript.
    files = {"file": ("meeting.txt", b"Client wants delivery by Friday.\nPrice agreed at 100.", "text/plain")}
    r = client.post("/ingest/audio", files=files, data={"lang": "en"})
    assert r.status_code == 200
    assert r.json()["segments"] >= 1


def test_delete_endpoint():
    client.post("/ingest/text", json={"text": "temporary memory", "lang": "en"})
    r = client.delete("/data")
    assert r.status_code == 200
    assert r.json()["deleted_segments"] >= 1
