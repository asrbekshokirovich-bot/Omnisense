"""Per-tenant API keys — the Phase-0 way to authenticate non-developer clients.

X-API-Key sent by a mobile/server client → tenant_id. The dev X-User-Id header still
works as a shortcut for local testing (the demo + tests rely on it), but in
production a real client must send an API key.

Phase 0 stores keys in memory; persistence is a Phase-1 task (move to Postgres
alongside subscriptions). The interface here is deliberately small so the
Postgres-backed implementation drops in without touching call sites.

Format: keys are random 32-byte hex strings prefixed with `omni_`. Plaintext is shown
ONCE at creation; the server only ever stores the sha-256 hash, so a key compromised
client-side is the only way the actual value leaks. Revocation deletes the hash → next
request from that key gets 401.
"""
from __future__ import annotations

import hashlib
import secrets
import time
from dataclasses import dataclass, field


def _new_key() -> str:
    return f"omni_{secrets.token_hex(32)}"


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _mask(plain: str) -> str:
    """Shown in /apikeys lists. e.g. 'omni_a1b2…f9e8'."""
    if len(plain) <= 8:
        return plain
    return f"{plain[:6]}…{plain[-4:]}"


@dataclass
class ApiKeyRecord:
    key_id: str
    tenant_id: str
    label: str
    hashed: str = field(repr=False)
    masked: str
    created_at: float = field(default_factory=time.time)
    last_used_at: float | None = None


class ApiKeyStore:
    """In-memory registry keyed by the sha-256 hash of the plaintext."""

    def __init__(self) -> None:
        self._by_hash: dict[str, ApiKeyRecord] = {}
        self._by_id: dict[str, ApiKeyRecord] = {}

    # ---- mutation -----------------------------------------------------------
    def create(self, tenant_id: str, label: str = "") -> tuple[str, ApiKeyRecord]:
        """Mint a new key for a tenant. Returns the plaintext (only chance to see it)
        and the record (without the plaintext)."""
        plaintext = _new_key()
        key_id = secrets.token_hex(8)
        rec = ApiKeyRecord(
            key_id=key_id,
            tenant_id=tenant_id,
            label=(label or "").strip()[:64],
            hashed=_hash(plaintext),
            masked=_mask(plaintext),
        )
        self._by_hash[rec.hashed] = rec
        self._by_id[rec.key_id] = rec
        return plaintext, rec

    def revoke(self, key_id: str, tenant_id: str) -> bool:
        """Tenant-scoped revoke — revoking someone else's key_id is a no-op (no leak)."""
        rec = self._by_id.get(key_id)
        if rec is None or rec.tenant_id != tenant_id:
            return False
        self._by_id.pop(rec.key_id, None)
        self._by_hash.pop(rec.hashed, None)
        return True

    # ---- query --------------------------------------------------------------
    def resolve(self, plaintext: str) -> ApiKeyRecord | None:
        rec = self._by_hash.get(_hash(plaintext))
        if rec is not None:
            rec.last_used_at = time.time()
        return rec

    def list_for_tenant(self, tenant_id: str) -> list[dict]:
        out = []
        for rec in self._by_id.values():
            if rec.tenant_id == tenant_id:
                out.append({
                    "key_id": rec.key_id,
                    "label": rec.label,
                    "masked": rec.masked,
                    "created_at": rec.created_at,
                    "last_used_at": rec.last_used_at,
                })
        out.sort(key=lambda r: r["created_at"], reverse=True)
        return out
