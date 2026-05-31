"""Per-tenant usage counters.

Phase-0 skeleton for the eventual billing/quota story (docs/business-plan.md — Personal
~$2 / Pro ~$4 / Business seats). Tracks the things we will price on: how many segments
were ingested, how many questions answered, how many briefings generated, and the last
time the tenant was active.

In-memory only — restarts reset the counter. That is fine for the demo and Phase-0; real
production will persist this in Postgres (the tenant_id column already exists) once the
auth layer is real. The interface here is deliberately small so a Postgres-backed
implementation drops in without touching call sites.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class TenantUsage:
    tenant_id: str
    segments_ingested: int = 0
    questions_asked: int = 0
    briefings_generated: int = 0
    last_active_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "segments_ingested": self.segments_ingested,
            "questions_asked": self.questions_asked,
            "briefings_generated": self.briefings_generated,
            "last_active_at": self.last_active_at,
        }


class UsageMeter:
    def __init__(self) -> None:
        self._tenants: dict[str, TenantUsage] = {}

    def _get(self, tenant_id: str) -> TenantUsage:
        u = self._tenants.get(tenant_id)
        if u is None:
            u = TenantUsage(tenant_id=tenant_id)
            self._tenants[tenant_id] = u
        return u

    def record_ingest(self, tenant_id: str, segments: int) -> None:
        u = self._get(tenant_id)
        u.segments_ingested += max(0, int(segments))
        u.last_active_at = time.time()

    def record_question(self, tenant_id: str) -> None:
        u = self._get(tenant_id)
        u.questions_asked += 1
        u.last_active_at = time.time()

    def record_briefing(self, tenant_id: str) -> None:
        u = self._get(tenant_id)
        u.briefings_generated += 1
        u.last_active_at = time.time()

    def get(self, tenant_id: str) -> dict:
        return self._get(tenant_id).to_dict()

    def reset(self, tenant_id: str) -> None:
        self._tenants.pop(tenant_id, None)
