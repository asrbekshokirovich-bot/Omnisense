"""Per-tenant subscription state + a small provider abstraction for Payme / Click.

Phase 0 ships the *shape* — enough to demo "3 months free, then $2/mo Personal" without
the merchant integration being real. The model maps to the business plan
(`docs/business-plan.md`):

  - **Trial first.** Every new tenant gets a 90-day free trial. The countdown starts
    on `start_trial()` and is visible in /billing.
  - **Plans.** "personal", "pro", "business" — the three lines from the plan. Prices
    live in centsom (1 som = 100 centsom) so we never lose precision on USD↔UZS math.
  - **Provider.** Real production is **Payme** + **Click** + carrier billing + BNPL
    (see `docs/business-plan.md` GTM). The integrations are merchant-bound (require a
    live contract and webhook URL), so this file ships **stubs** behind a
    `BillingProvider` interface. The mock provider runs the API end-to-end offline so
    the demo + tests work without touching a merchant.

What this file is NOT:
  - A complete subscription engine. No prorations, no dunning, no taxes.
  - A finance system. Real revenue recognition lives in Postgres + Stripe-style events;
    Phase 0 tracks state in memory.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .config import Settings


# Catalog: amounts are in **centsom** (1 som = 100 centsom). Personal/Pro target the
# numbers from docs/business-plan.md; Business is per-seat / month.
PLAN_CATALOG: dict[str, dict] = {
    "personal": {"price_centsom": 2_500_00, "billing_cycle_months": 1,
                 "annual_centsom": 24_000_00,  # ≈ $2/mo with annual discount
                 "label": "Personal"},
    "pro":      {"price_centsom": 5_000_00, "billing_cycle_months": 1,
                 "annual_centsom": 48_000_00,
                 "label": "Pro"},
    "business": {"price_centsom": 15_000_00, "billing_cycle_months": 1,
                 "annual_centsom": 144_000_00,
                 "label": "Business (per seat)"},
}

VALID_PROVIDERS = ("mock", "payme", "click")

# 3 months free, the business-plan promise. Computed as 90 days to keep month-length
# ambiguity out of the model — the team can swap to calendar months if/when needed.
TRIAL_DAYS = 90


@dataclass
class Subscription:
    tenant_id: str
    status: str = "none"  # none | trialing | active | past_due | canceled
    plan: str | None = None
    trial_started_at: float | None = None
    current_period_end: float | None = None  # epoch seconds; relevant for trialing/active
    provider: str | None = None
    last_event_at: float = field(default_factory=time.time)
    annual: bool = False

    def to_dict(self) -> dict:
        days_left = None
        if self.current_period_end:
            days_left = max(0, int((self.current_period_end - time.time()) // 86400))
        return {
            "tenant_id": self.tenant_id,
            "status": self.status,
            "plan": self.plan,
            "annual": self.annual,
            "provider": self.provider,
            "trial_started_at": self.trial_started_at,
            "current_period_end": self.current_period_end,
            "days_remaining": days_left,
            "last_event_at": self.last_event_at,
        }


class SubscriptionStore:
    """Per-tenant subscription state. In-memory for Phase 0 — Postgres-backed real
    implementation drops in without changing call sites."""

    def __init__(self) -> None:
        self._by_tenant: dict[str, Subscription] = {}

    def get(self, tenant_id: str) -> Subscription:
        sub = self._by_tenant.get(tenant_id)
        if sub is None:
            sub = Subscription(tenant_id=tenant_id)
            self._by_tenant[tenant_id] = sub
        return sub

    def start_trial(self, tenant_id: str) -> Subscription:
        sub = self.get(tenant_id)
        if sub.status == "trialing":
            return sub  # idempotent — re-calling /start-trial is a no-op
        if sub.status in ("active", "past_due"):
            # Already paying. Trial only applies to brand-new tenants.
            return sub
        now = time.time()
        sub.status = "trialing"
        sub.trial_started_at = now
        sub.current_period_end = now + TRIAL_DAYS * 86400
        sub.last_event_at = now
        return sub

    def activate(self, tenant_id: str, plan: str, provider: str,
                 annual: bool = False) -> Subscription:
        if plan not in PLAN_CATALOG:
            raise ValueError(f"unknown plan: {plan!r}")
        if provider not in VALID_PROVIDERS:
            raise ValueError(f"unknown provider: {provider!r}")
        sub = self.get(tenant_id)
        sub.status = "active"
        sub.plan = plan
        sub.provider = provider
        sub.annual = annual
        period = PLAN_CATALOG[plan]["billing_cycle_months"]
        sub.current_period_end = time.time() + (
            365 if annual else 30 * period
        ) * 86400
        sub.last_event_at = time.time()
        return sub

    def mark_past_due(self, tenant_id: str) -> Subscription:
        sub = self.get(tenant_id)
        sub.status = "past_due"
        sub.last_event_at = time.time()
        return sub

    def cancel(self, tenant_id: str) -> Subscription:
        sub = self.get(tenant_id)
        sub.status = "canceled"
        sub.last_event_at = time.time()
        return sub


# ---- BillingProvider abstraction --------------------------------------------
class BillingProvider:
    """Interface for a payments backend. Two methods:

      - `create_payment(plan, tenant_id, annual)` — returns a dict describing the next
        client action (usually a hosted-checkout URL or a deeplink to the provider's
        app). The real Payme/Click flows are out-of-band; we just return the prepared
        intent.
      - `handle_webhook(event)` — called by FastAPI when the provider POSTs a
        completion / failure callback. Returns the (verb, tenant_id) it derived so the
        endpoint can update SubscriptionStore.
    """

    name: str = "provider"

    def create_payment(self, plan: str, tenant_id: str, annual: bool) -> dict:
        raise NotImplementedError

    def handle_webhook(self, event: dict) -> dict:
        raise NotImplementedError


class MockBilling(BillingProvider):
    """Offline provider: every create_payment returns a fake URL and every webhook is
    accepted as a paid event. Used by the demo + tests."""

    name = "mock"

    def create_payment(self, plan: str, tenant_id: str, annual: bool) -> dict:
        if plan not in PLAN_CATALOG:
            raise ValueError(f"unknown plan: {plan!r}")
        amount = PLAN_CATALOG[plan][
            "annual_centsom" if annual else "price_centsom"
        ]
        return {
            "provider": self.name,
            "redirect_url": f"https://omnisense.local/checkout/mock?tenant={tenant_id}&plan={plan}",
            "amount_centsom": amount,
            "annual": annual,
            "intent_id": f"mock-{tenant_id}-{plan}-{int(time.time())}",
        }

    def handle_webhook(self, event: dict) -> dict:
        # event shape: {"intent_id": str, "status": "paid"|"failed", ...}
        # The intent id encodes "mock-<tenant>-<plan>-<ts>".
        intent = str(event.get("intent_id", ""))
        parts = intent.split("-")
        if len(parts) < 4 or parts[0] != "mock":
            raise ValueError("invalid mock intent_id")
        tenant_id = parts[1]
        plan = parts[2]
        return {
            "tenant_id": tenant_id,
            "plan": plan,
            "verb": "paid" if event.get("status") == "paid" else "failed",
        }


def make_billing(s: Settings) -> BillingProvider:
    """Phase 0 always returns the mock provider. Real Payme/Click adapters live in
    app/providers/billing_payme.py + billing_click.py once the merchant contract lands
    — they will be lazy-imported the same way Anthropic/Yandex are today."""
    if s.billing_provider == "payme":
        from .providers.billing_payme import PaymeBilling  # lazy
        return PaymeBilling(s)
    if s.billing_provider == "click":
        from .providers.billing_click import ClickBilling  # lazy
        return ClickBilling(s)
    return MockBilling()
