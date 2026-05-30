"""In-memory token-bucket rate limiter — per tenant.

Token bucket because it gives a clean separation between sustained rate (refill speed)
and burst tolerance (capacity). Phase 0 default: 60 requests/min sustained, burst of
10 — generous enough for the demo, tight enough that a runaway loop is obvious.

In-memory means restarts reset the counters; that is fine for Phase 0 since we don't
bill on rate today. Phase-1 swaps the backend for Redis (the `infra/docker-compose.yml`
already runs one) without changing call sites — same interface.

Returns the seconds the client should wait before retrying. The HTTP layer converts
that to a 429 with `Retry-After`.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class _Bucket:
    tokens: float
    last_refill: float


@dataclass
class RateLimit:
    """Per-tenant overrides; absent fields fall back to the limiter defaults."""
    rate_per_min: float | None = None
    burst: float | None = None


class TokenBucketLimiter:
    def __init__(self, rate_per_min: float = 60.0, burst: float = 10.0) -> None:
        if rate_per_min <= 0 or burst <= 0:
            raise ValueError("rate_per_min and burst must be positive")
        self.rate_per_sec = rate_per_min / 60.0
        self.burst = float(burst)
        self._buckets: dict[str, _Bucket] = {}
        self._overrides: dict[str, RateLimit] = {}
        # Test hook — tests inject a deterministic clock instead of monkeypatching time.
        self._clock = time.monotonic

    # ---- per-tenant tuning --------------------------------------------------
    def set_override(self, tenant_id: str, rate_per_min: float | None = None,
                     burst: float | None = None) -> None:
        self._overrides[tenant_id] = RateLimit(rate_per_min=rate_per_min, burst=burst)
        # Drop any cached bucket so the new caps take effect on the next call.
        self._buckets.pop(tenant_id, None)

    def _params(self, tenant_id: str) -> tuple[float, float]:
        ov = self._overrides.get(tenant_id)
        rate = (ov.rate_per_min / 60.0) if (ov and ov.rate_per_min is not None) else self.rate_per_sec
        burst = (ov.burst if (ov and ov.burst is not None) else self.burst)
        return rate, burst

    # ---- the call -----------------------------------------------------------
    def acquire(self, tenant_id: str, cost: float = 1.0) -> tuple[bool, float]:
        """Try to consume `cost` tokens. Returns (allowed, retry_after_seconds).
        retry_after is 0.0 when allowed."""
        rate, burst = self._params(tenant_id)
        now = self._clock()
        b = self._buckets.get(tenant_id)
        if b is None:
            b = _Bucket(tokens=burst, last_refill=now)
            self._buckets[tenant_id] = b
        # Refill — bounded by capacity.
        elapsed = max(0.0, now - b.last_refill)
        b.tokens = min(burst, b.tokens + elapsed * rate)
        b.last_refill = now
        if b.tokens >= cost:
            b.tokens -= cost
            return True, 0.0
        deficit = cost - b.tokens
        retry_after = deficit / rate if rate > 0 else float("inf")
        return False, retry_after

    def peek(self, tenant_id: str) -> dict:
        """Diagnostic — current bucket state, for /health or test asserts."""
        rate, burst = self._params(tenant_id)
        b = self._buckets.get(tenant_id)
        return {
            "tenant_id": tenant_id,
            "rate_per_min": rate * 60.0,
            "burst": burst,
            "tokens_available": round(b.tokens, 4) if b else burst,
        }
