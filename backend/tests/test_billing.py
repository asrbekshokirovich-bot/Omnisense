"""Billing skeleton tests — subscription state, mock provider, webhook flow."""
from __future__ import annotations

import time

import pytest


# ---- SubscriptionStore --------------------------------------------------
def test_trial_is_90_days_and_idempotent():
    from app.billing import TRIAL_DAYS, SubscriptionStore

    store = SubscriptionStore()
    sub = store.start_trial("alice")
    assert sub.status == "trialing"
    assert TRIAL_DAYS == 90  # business-plan promise: 3 months free

    days_left = (sub.current_period_end - time.time()) / 86400
    assert 89 <= days_left <= 90

    # Idempotent — re-calling doesn't reset the clock.
    end_before = sub.current_period_end
    time.sleep(0.01)
    again = store.start_trial("alice")
    assert again.current_period_end == end_before


def test_activate_advances_period_end():
    from app.billing import SubscriptionStore

    store = SubscriptionStore()
    sub = store.activate("alice", "pro", provider="mock")
    assert sub.status == "active"
    assert sub.plan == "pro"
    # Default monthly cycle → ~30 days.
    days_left = (sub.current_period_end - time.time()) / 86400
    assert 29 <= days_left <= 30

    # Annual gives ~365 days.
    annual = store.activate("alice", "pro", provider="mock", annual=True)
    days_left = (annual.current_period_end - time.time()) / 86400
    assert 364 <= days_left <= 365
    assert annual.annual is True


def test_activate_rejects_unknown_plan_and_provider():
    from app.billing import SubscriptionStore

    store = SubscriptionStore()
    with pytest.raises(ValueError):
        store.activate("alice", "platinum", provider="mock")
    with pytest.raises(ValueError):
        store.activate("alice", "personal", provider="stripe")


def test_mark_past_due_and_cancel():
    from app.billing import SubscriptionStore

    store = SubscriptionStore()
    store.activate("alice", "personal", provider="mock")
    assert store.mark_past_due("alice").status == "past_due"
    assert store.cancel("alice").status == "canceled"


# ---- MockBilling provider -----------------------------------------------
def test_mock_provider_round_trip():
    from app.billing import MockBilling

    b = MockBilling()
    intent = b.create_payment("personal", "alice", annual=False)
    assert intent["provider"] == "mock"
    assert intent["amount_centsom"] == 2_500_00
    assert "alice" in intent["redirect_url"]

    parsed = b.handle_webhook({"intent_id": intent["intent_id"], "status": "paid"})
    assert parsed == {"tenant_id": "alice", "plan": "personal", "verb": "paid"}

    parsed = b.handle_webhook({"intent_id": intent["intent_id"], "status": "failed"})
    assert parsed["verb"] == "failed"


def test_mock_provider_rejects_unknown_plan():
    from app.billing import MockBilling
    with pytest.raises(ValueError):
        MockBilling().create_payment("platinum", "alice", annual=False)


# ---- API ---------------------------------------------------------------
def test_billing_endpoints_flow(monkeypatch):
    """Full /billing/start-trial → /billing/subscribe → /billing/webhook flow."""
    from fastapi.testclient import TestClient

    import app.main as main_mod
    from app.config import Settings
    from app.pipeline import Pipeline

    monkeypatch.setattr(main_mod, "pipeline", Pipeline(Settings()))
    client = TestClient(main_mod.app)
    h = {"X-User-Id": "alice"}

    # No subscription yet.
    r = client.get("/billing", headers=h)
    assert r.json()["subscription"]["status"] == "none"
    assert "personal" in r.json()["catalog"]

    # Start trial.
    r = client.post("/billing/start-trial", headers=h)
    assert r.json()["status"] == "trialing"
    assert r.json()["days_remaining"] is not None and r.json()["days_remaining"] >= 89

    # Subscribe (paid).
    r = client.post("/billing/subscribe", json={"plan": "pro", "annual": True}, headers=h)
    intent = r.json()
    assert intent["amount_centsom"] == 48_000_00

    # Webhook: paid → active.
    r = client.post("/billing/webhook/mock",
                    json={"intent_id": intent["intent_id"], "status": "paid", "annual": True})
    body = r.json()
    assert body["ok"] is True
    assert body["subscription"]["status"] == "active"
    assert body["subscription"]["plan"] == "pro"
    assert body["subscription"]["annual"] is True


def test_billing_subscribe_rejects_unknown_plan(monkeypatch):
    from fastapi.testclient import TestClient

    import app.main as main_mod
    from app.config import Settings
    from app.pipeline import Pipeline

    monkeypatch.setattr(main_mod, "pipeline", Pipeline(Settings()))
    client = TestClient(main_mod.app)
    r = client.post("/billing/subscribe", json={"plan": "platinum"},
                    headers={"X-User-Id": "alice"})
    assert r.status_code == 400


def test_billing_webhook_provider_mismatch(monkeypatch):
    """A Payme webhook hitting a mock-configured server must be rejected, not silently
    accepted — otherwise a misconfigured deploy quietly applies the wrong events."""
    from fastapi.testclient import TestClient

    import app.main as main_mod
    from app.config import Settings
    from app.pipeline import Pipeline

    monkeypatch.setattr(main_mod, "pipeline", Pipeline(Settings()))
    client = TestClient(main_mod.app)
    r = client.post("/billing/webhook/payme", json={"intent_id": "x", "status": "paid"})
    assert r.status_code == 400


def test_billing_subscription_isolated_per_tenant(monkeypatch):
    from fastapi.testclient import TestClient

    import app.main as main_mod
    from app.config import Settings
    from app.pipeline import Pipeline

    monkeypatch.setattr(main_mod, "pipeline", Pipeline(Settings()))
    client = TestClient(main_mod.app)
    client.post("/billing/start-trial", headers={"X-User-Id": "alice"})
    alice = client.get("/billing", headers={"X-User-Id": "alice"}).json()
    bob = client.get("/billing", headers={"X-User-Id": "bob"}).json()
    assert alice["subscription"]["status"] == "trialing"
    assert bob["subscription"]["status"] == "none"


# ---- Stub-provider safety guard -----------------------------------------
def test_payme_stub_fails_loud():
    """Don't let an OMNI_BILLING=payme deploy silently pretend to work."""
    from app.config import Settings
    from app.billing import make_billing
    with pytest.raises(NotImplementedError):
        make_billing(Settings(billing_provider="payme"))


def test_click_stub_fails_loud():
    from app.config import Settings
    from app.billing import make_billing
    with pytest.raises(NotImplementedError):
        make_billing(Settings(billing_provider="click"))
