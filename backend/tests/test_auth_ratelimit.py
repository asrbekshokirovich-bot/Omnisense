"""API keys, token-bucket rate limiter, X-Request-Id propagation."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ---- ApiKeyStore unit tests ---------------------------------------------
def test_api_key_create_returns_plaintext_once_and_resolves():
    from app.auth import ApiKeyStore

    store = ApiKeyStore()
    plaintext, rec = store.create("alice", label="phone")
    assert plaintext.startswith("omni_")
    # Resolution finds the tenant.
    found = store.resolve(plaintext)
    assert found is not None
    assert found.tenant_id == "alice"
    assert found.label == "phone"
    # Masked form does NOT contain the full key.
    assert plaintext != rec.masked
    assert rec.masked.startswith("omni_")
    assert "…" in rec.masked


def test_api_key_resolve_returns_none_for_unknown():
    from app.auth import ApiKeyStore
    assert ApiKeyStore().resolve("omni_bogus") is None


def test_api_key_revoke_is_tenant_scoped():
    from app.auth import ApiKeyStore

    store = ApiKeyStore()
    _, alice = store.create("alice")
    _, _bob = store.create("bob")
    # bob can't revoke alice's key.
    assert store.revoke(alice.key_id, "bob") is False
    assert store.revoke(alice.key_id, "alice") is True
    # Same id twice is a no-op.
    assert store.revoke(alice.key_id, "alice") is False


def test_api_key_list_only_shows_caller_keys():
    from app.auth import ApiKeyStore

    store = ApiKeyStore()
    store.create("alice"); store.create("alice"); store.create("bob")
    assert len(store.list_for_tenant("alice")) == 2
    assert len(store.list_for_tenant("bob")) == 1


# ---- Token-bucket limiter unit tests ------------------------------------
def test_rate_limiter_allows_burst_then_refuses():
    from app.ratelimit import TokenBucketLimiter

    # Deterministic clock — we step it explicitly.
    now = [1000.0]
    rl = TokenBucketLimiter(rate_per_min=60, burst=3)
    rl._clock = lambda: now[0]

    assert rl.acquire("t") == (True, 0.0)
    assert rl.acquire("t") == (True, 0.0)
    assert rl.acquire("t") == (True, 0.0)
    allowed, retry = rl.acquire("t")
    assert allowed is False
    # 60/min = 1/sec; deficit 1.0 → 1.0 s retry.
    assert pytest.approx(retry, abs=1e-3) == 1.0


def test_rate_limiter_refills_over_time():
    from app.ratelimit import TokenBucketLimiter

    now = [1000.0]
    rl = TokenBucketLimiter(rate_per_min=60, burst=1)
    rl._clock = lambda: now[0]

    assert rl.acquire("t")[0]
    assert rl.acquire("t")[0] is False
    # 1.5 s later → 1 token refilled → allowed again.
    now[0] += 1.5
    assert rl.acquire("t")[0]


def test_rate_limiter_per_tenant_independent():
    from app.ratelimit import TokenBucketLimiter

    rl = TokenBucketLimiter(rate_per_min=60, burst=1)
    assert rl.acquire("alice")[0]
    # Alice exhausted but bob still has burst.
    assert rl.acquire("bob")[0]


def test_rate_limiter_override():
    from app.ratelimit import TokenBucketLimiter

    now = [0.0]
    rl = TokenBucketLimiter(rate_per_min=60, burst=1)
    rl._clock = lambda: now[0]
    rl.set_override("vip", rate_per_min=120, burst=5)
    # VIP gets 5 immediately.
    for _ in range(5):
        assert rl.acquire("vip")[0]
    assert rl.acquire("vip")[0] is False


def test_rate_limiter_rejects_invalid_config():
    from app.ratelimit import TokenBucketLimiter
    with pytest.raises(ValueError):
        TokenBucketLimiter(rate_per_min=0)
    with pytest.raises(ValueError):
        TokenBucketLimiter(burst=0)


# ---- API integration ----------------------------------------------------
@pytest.fixture
def client(monkeypatch):
    import app.main as main_mod
    from app.config import Settings
    from app.pipeline import Pipeline

    # Loose rate so the suite isn't flaky; specific tests turn the screws down.
    monkeypatch.setattr(main_mod, "pipeline",
                        Pipeline(Settings(rate_per_min=600.0, rate_burst=100.0)))
    return TestClient(main_mod.app)


def test_x_api_key_resolves_tenant(client):
    """A minted key authenticates as its owner — no X-User-Id needed."""
    minted = client.post("/apikeys", json={"label": "phone"},
                        headers={"X-User-Id": "alice"}).json()
    key = minted["api_key"]
    # Now use the key alone.
    r = client.post("/ingest/text", json={"text": "alice line", "lang": "en"},
                    headers={"X-API-Key": key})
    assert r.status_code == 200
    # And ask sees alice's memory.
    r = client.post("/ask", json={"question": "alice?", "lang": "en"},
                    headers={"X-API-Key": key})
    body = r.json()
    assert any("alice" in c["text"].lower() for c in body["citations"])


def test_x_api_key_wins_over_x_user_id(client):
    """Alice's key with bob's X-User-Id → still alice."""
    a = client.post("/apikeys", json={"label": "a"},
                    headers={"X-User-Id": "alice"}).json()["api_key"]
    client.post("/ingest/text", json={"text": "alice's only memory", "lang": "en"},
                headers={"X-API-Key": a}).raise_for_status()
    r = client.get("/sessions", headers={"X-API-Key": a, "X-User-Id": "bob"})
    assert len(r.json()["sessions"]) == 1


def test_invalid_x_api_key_returns_401(client):
    r = client.post("/ingest/text", json={"text": "x", "lang": "en"},
                    headers={"X-API-Key": "omni_definitely_bogus"})
    assert r.status_code == 401


def test_apikey_list_is_masked_and_tenant_scoped(client):
    alice_key = client.post("/apikeys", json={"label": "phone"},
                            headers={"X-User-Id": "alice"}).json()["api_key"]
    client.post("/apikeys", json={"label": "laptop"}, headers={"X-User-Id": "alice"})
    client.post("/apikeys", json={"label": "bob laptop"}, headers={"X-User-Id": "bob"})

    r = client.get("/apikeys", headers={"X-User-Id": "alice"}).json()
    assert len(r["keys"]) == 2
    # Plaintext is NOT in the list response.
    assert all(alice_key != k["masked"] for k in r["keys"])
    assert all("…" in k["masked"] for k in r["keys"])

    bob_keys = client.get("/apikeys", headers={"X-User-Id": "bob"}).json()["keys"]
    assert len(bob_keys) == 1


def test_apikey_revoke_blocks_subsequent_calls(client):
    minted = client.post("/apikeys", json={"label": "k"},
                         headers={"X-User-Id": "alice"}).json()
    key = minted["api_key"]; key_id = minted["key_id"]
    # Works before revoke.
    assert client.get("/sessions", headers={"X-API-Key": key}).status_code == 200
    client.delete(f"/apikeys/{key_id}", headers={"X-User-Id": "alice"})
    # Works after — no.
    assert client.get("/sessions", headers={"X-API-Key": key}).status_code == 401


def test_x_request_id_echoed_when_provided(client):
    r = client.get("/health", headers={"X-Request-Id": "abc-123"})
    assert r.headers["x-request-id"] == "abc-123"


def test_x_request_id_generated_when_missing(client):
    r = client.get("/health")
    rid = r.headers.get("x-request-id")
    assert rid and len(rid) >= 16


def test_rate_limit_returns_429_with_retry_after(monkeypatch):
    import app.main as main_mod
    from app.config import Settings
    from app.pipeline import Pipeline

    # 2 / min, burst 2 → first two requests pass, third 429.
    monkeypatch.setattr(main_mod, "pipeline",
                        Pipeline(Settings(rate_per_min=2.0, rate_burst=2.0)))
    client = TestClient(main_mod.app)
    h = {"X-User-Id": "alice"}
    assert client.post("/ingest/text", json={"text": "a", "lang": "en"}, headers=h).status_code == 200
    assert client.post("/ingest/text", json={"text": "b", "lang": "en"}, headers=h).status_code == 200
    r = client.post("/ingest/text", json={"text": "c", "lang": "en"}, headers=h)
    assert r.status_code == 429
    assert int(r.headers["retry-after"]) >= 1
    # Other tenants are not blocked by alice's exhaustion.
    assert client.post("/ingest/text", json={"text": "x", "lang": "en"},
                       headers={"X-User-Id": "bob"}).status_code == 200


def test_health_and_delete_are_not_rate_limited(monkeypatch):
    """Privacy operations (DELETE /data) and probes (/health) must never be
    rate-limited — never make 'delete me' or a load-balancer probe wait."""
    import app.main as main_mod
    from app.config import Settings
    from app.pipeline import Pipeline

    monkeypatch.setattr(main_mod, "pipeline",
                        Pipeline(Settings(rate_per_min=1.0, rate_burst=1.0)))
    client = TestClient(main_mod.app)
    h = {"X-User-Id": "alice"}
    # Burn the single token.
    client.post("/ingest/text", json={"text": "x", "lang": "en"}, headers=h)
    # /health and DELETE /data still go through.
    assert client.get("/health", headers=h).status_code == 200
    assert client.delete("/data", headers=h).status_code == 200
