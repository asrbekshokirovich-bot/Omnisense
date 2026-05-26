"""Payme (paycom.uz) billing adapter — STUB.

This is the shape we will fill in once the team has:
  - A Payme merchant ID (`PAYME_MERCHANT_ID`).
  - The two webhook secrets Payme issues per merchant.
  - The chosen integration model: hosted checkout (Pay-form) vs. their JSON-RPC
    Merchant API. Hosted is faster to ship; JSON-RPC gives more control.

Real implementation reference: https://developer.help.paycom.uz/

What stays the same:
  - create_payment(plan, tenant_id, annual) returns {provider, redirect_url, amount,
    intent_id} — the API contract is the same as MockBilling so the FastAPI layer
    does not change when this adapter ships.
  - handle_webhook(event) verifies the Payme signature and returns
    {tenant_id, plan, verb}. The endpoint layer (app/main.py) then calls
    SubscriptionStore.activate / mark_past_due.

The class raises a clear NotImplementedError now so any accidental OMNI_BILLING=payme
configuration fails loud rather than silently letting "no-op billing" run.
"""
from __future__ import annotations

from ..billing import BillingProvider
from ..config import Settings


class PaymeBilling(BillingProvider):
    name = "payme"

    def __init__(self, s: Settings) -> None:
        raise NotImplementedError(
            "Payme adapter is a Phase 1 task — needs the merchant contract and the "
            "webhook secrets. The interface (create_payment / handle_webhook) is "
            "fixed; fill in the body when credentials land."
        )
