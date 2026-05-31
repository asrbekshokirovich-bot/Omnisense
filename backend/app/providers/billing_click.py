"""Click (click.uz) billing adapter — STUB.

Same shape as PaymeBilling. Fill in once the team has:
  - A Click merchant id (`CLICK_MERCHANT_ID`) + service id.
  - The shared secret used to sign their Prepare / Complete callbacks.
  - The chosen integration model: Click-UP Pay (deeplink) vs. their Shop-API
    (server-to-server).

Real implementation reference: https://docs.click.uz/

API contract is identical to MockBilling so the FastAPI layer is unaffected when
this lands.
"""
from __future__ import annotations

from ..billing import BillingProvider
from ..config import Settings


class ClickBilling(BillingProvider):
    name = "click"

    def __init__(self, s: Settings) -> None:
        raise NotImplementedError(
            "Click adapter is a Phase 1 task — needs the merchant credentials. The "
            "interface (create_payment / handle_webhook) is fixed; fill in the body "
            "when credentials land."
        )
