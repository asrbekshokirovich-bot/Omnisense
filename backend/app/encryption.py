"""Envelope encryption for segment text + voiceprints at rest.

Design (Phase 0):
  - One server-held **KEK** (key encryption key) — read from `OMNI_KEK` (urlsafe-b64
    32 bytes). In production this lives in HashiCorp Vault / KMS / Yandex Cloud KMS
    — Phase 0 reads it from env so the team can wire it up without infra dependencies.
  - One per-tenant **DEK** (data encryption key) derived deterministically from the
    KEK via HKDF-SHA256 with `info="omni-dek-v1:" + tenant_id`. Deterministic so
    restarts don't lose access — the KEK is the only secret that ever needs to be
    persisted; revoke a tenant by rotating the KEK or extending HKDF info to add a
    revocation epoch.
  - Each value (segment text, voiceprint blob) is encrypted with the tenant's DEK
    using **Fernet** (AES-128-CBC + HMAC-SHA256; AEAD-equivalent; built into
    `cryptography`). Ciphertexts carry their own IV + timestamp + auth tag.

Why deterministic-DEK and not store-per-tenant-DEK-encrypted-by-KEK?
  - In-memory tenant state in Phase 0 means we'd have to persist DEKs immediately
    or re-derive on every cold start, and the Postgres tenants table doesn't exist
    yet. Deterministic derivation gives the same crypto guarantees (each tenant gets
    a unique key, only KEK exposure compromises all) without the persistence shape.
  - It's symmetric with the consent log + owner-voiceprint per-tenant file naming.

Migration path: when tenants are first-class in Postgres, swap to
"DEK = random; persisted-wrapped-by-KEK" — same Encryptor interface, no call-site
changes.

The default is MockEncryptor (passthrough) so the offline demo + tests are not
disturbed. Set `OMNI_ENCRYPTION=fernet` plus `OMNI_KEK=<urlsafe-b64-32-bytes>` to
turn it on.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class Encryptor(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def encrypt(self, plaintext: str, tenant_id: str) -> str:
        """Encrypt a UTF-8 string. Returns an ASCII ciphertext (safe to store in TEXT
        columns / JSON / files)."""

    @abstractmethod
    def decrypt(self, ciphertext: str, tenant_id: str) -> str:
        """Decrypt. If the ciphertext was produced by a different tenant's DEK the
        decryption fails (which is the correct cross-tenant safety property)."""


class MockEncryptor(Encryptor):
    """No-op passthrough. The default — keeps tests and the offline demo identical to
    pre-encryption behavior."""

    name = "mock"

    def encrypt(self, plaintext: str, tenant_id: str) -> str:
        return plaintext

    def decrypt(self, ciphertext: str, tenant_id: str) -> str:
        return ciphertext


class FernetEncryptor(Encryptor):
    """Production-grade. Lazy-imports `cryptography` so the offline default install
    doesn't need it."""

    name = "fernet"

    def __init__(self, kek_b64: str) -> None:
        if not kek_b64:
            raise ValueError("OMNI_KEK is required for OMNI_ENCRYPTION=fernet")
        import base64
        # Validate the KEK is a proper Fernet-compatible 32-byte urlsafe-b64 blob.
        try:
            kek_bytes = base64.urlsafe_b64decode(kek_b64.encode("utf-8"))
        except Exception as e:
            raise ValueError(f"OMNI_KEK is not valid urlsafe-base64: {e}") from None
        if len(kek_bytes) != 32:
            raise ValueError(
                f"OMNI_KEK must decode to 32 bytes (got {len(kek_bytes)}). "
                "Generate with: python -c \"import secrets,base64;"
                "print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())\""
            )
        self._kek_bytes = kek_bytes
        self._dek_cache: dict[str, "_FernetCipher"] = {}

    def _dek(self, tenant_id: str):
        cached = self._dek_cache.get(tenant_id)
        if cached is not None:
            return cached
        import base64
        from cryptography.fernet import Fernet  # lazy
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF

        derived = HKDF(
            algorithm=hashes.SHA256(),
            length=32, salt=None,
            info=f"omni-dek-v1:{tenant_id}".encode("utf-8"),
        ).derive(self._kek_bytes)
        cipher = Fernet(base64.urlsafe_b64encode(derived))
        self._dek_cache[tenant_id] = cipher
        return cipher

    def encrypt(self, plaintext: str, tenant_id: str) -> str:
        return self._dek(tenant_id).encrypt(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, ciphertext: str, tenant_id: str) -> str:
        return self._dek(tenant_id).decrypt(ciphertext.encode("ascii")).decode("utf-8")


# Type alias for the lazy import path above.
_FernetCipher = object


def make_encryptor(provider: str, kek: str) -> Encryptor:
    if provider == "fernet":
        return FernetEncryptor(kek)
    return MockEncryptor()
