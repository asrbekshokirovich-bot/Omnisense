"""Encryption-at-rest tests: Encryptor interface + Fernet round-trip + pipeline wiring.

The cryptography package is an optional install. If it's not present we skip the Fernet
tests but still exercise MockEncryptor + the Pipeline-with-mock path.
"""
from __future__ import annotations

import base64
import secrets

import pytest

cryptography = pytest.importorskip("cryptography",
                                    reason="cryptography not installed — Fernet path skipped")


def _kek() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")


# ---- MockEncryptor (default, always available) -------------------------
def test_mock_encryptor_is_passthrough():
    from app.encryption import MockEncryptor

    e = MockEncryptor()
    assert e.encrypt("hello", "alice") == "hello"
    assert e.decrypt("hello", "alice") == "hello"


# ---- FernetEncryptor ---------------------------------------------------
def test_fernet_round_trip_per_tenant():
    from app.encryption import FernetEncryptor

    e = FernetEncryptor(_kek())
    a = e.encrypt("alice's plan is to ship Friday", "alice")
    assert "alice's plan" not in a  # ciphertext doesn't leak plaintext
    assert e.decrypt(a, "alice") == "alice's plan is to ship Friday"


def test_fernet_wrong_tenant_decryption_fails():
    """Cross-tenant attempt must error — alice's ciphertext is unreadable by bob even
    on the same server with the same KEK."""
    from app.encryption import FernetEncryptor
    from cryptography.fernet import InvalidToken

    e = FernetEncryptor(_kek())
    a_ct = e.encrypt("alice's secret", "alice")
    with pytest.raises(InvalidToken):
        e.decrypt(a_ct, "bob")


def test_fernet_same_kek_same_dek_across_processes_simulated():
    """Different FernetEncryptor instances built from the SAME KEK must derive the
    same DEK per tenant — otherwise restarting the server would lose access to all
    previously-encrypted data."""
    from app.encryption import FernetEncryptor

    kek = _kek()
    e1 = FernetEncryptor(kek)
    e2 = FernetEncryptor(kek)
    ct = e1.encrypt("survive restart", "alice")
    assert e2.decrypt(ct, "alice") == "survive restart"


def test_fernet_different_kek_cannot_decrypt():
    """Rotating the KEK invalidates every prior ciphertext (the way crypto-erase works
    at scale). Make this explicit so we don't accidentally key-share."""
    from app.encryption import FernetEncryptor
    from cryptography.fernet import InvalidToken

    e1 = FernetEncryptor(_kek())
    e2 = FernetEncryptor(_kek())
    ct = e1.encrypt("rotation test", "alice")
    with pytest.raises(InvalidToken):
        e2.decrypt(ct, "alice")


def test_fernet_rejects_missing_or_malformed_kek():
    from app.encryption import FernetEncryptor

    with pytest.raises(ValueError):
        FernetEncryptor("")
    with pytest.raises(ValueError):
        FernetEncryptor("not-base64???!!!")
    # Wrong length (24 bytes instead of 32).
    short = base64.urlsafe_b64encode(secrets.token_bytes(24)).decode()
    with pytest.raises(ValueError):
        FernetEncryptor(short)


# ---- Pipeline integration -----------------------------------------------
def test_pipeline_encrypts_at_rest_and_decrypts_on_read():
    """With OMNI_ENCRYPTION=fernet:
      - segment.text in the store is ciphertext (regulators-at-rest property).
      - /ask citations expose the plaintext (the user-facing decrypt).
    """
    from app.config import Settings
    from app.pipeline import Pipeline

    p = Pipeline(Settings(encryption="fernet", kek_b64=_kek()))
    p.delete_all()
    p.ingest_text("We ship the demo on Friday", lang="en")

    # On-disk shape: ciphertext.
    raw = p.store.all_segments("default")
    assert "Friday" not in raw[0].text
    # In production this segment would round-trip through Postgres as a TEXT column;
    # Fernet's ASCII output is safe to store unmodified.
    assert raw[0].text.startswith("gAAAAA")  # Fernet token marker

    # Recall path returns plaintext.
    out = p.ask("when?", lang="en")
    assert any("Friday" in c["text"] for c in out["citations"])


def test_pipeline_mock_encryption_is_default():
    """Sanity: by default the pipeline does not encrypt — keeps the offline demo +
    existing tests behavior intact."""
    from app.config import Settings
    from app.pipeline import Pipeline

    p = Pipeline(Settings())
    assert p.encryptor.name == "mock"
    p.delete_all()
    p.ingest_text("plain plaintext", lang="en")
    raw = p.store.all_segments("default")
    assert raw[0].text == "plain plaintext"


def test_pipeline_tenant_isolation_at_rest():
    """Two tenants encrypting on the same pipeline → each tenant's ciphertext is
    unreadable by the other even though both use the same KEK."""
    from app.config import Settings
    from app.pipeline import Pipeline

    p = Pipeline(Settings(encryption="fernet", kek_b64=_kek()))
    p.delete_all()
    p.ingest_text("alice's plan", lang="en", tenant_id="alice")
    p.ingest_text("bob's plan",   lang="en", tenant_id="bob")

    alice_raw = p.store.all_segments("alice")[0]
    bob_raw = p.store.all_segments("bob")[0]
    # Each tenant decrypts only their own.
    assert p.encryptor.decrypt(alice_raw.text, "alice") == "alice's plan"
    assert p.encryptor.decrypt(bob_raw.text, "bob") == "bob's plan"
    # And not the other's — cross-tenant decryption fails.
    from cryptography.fernet import InvalidToken
    with pytest.raises(InvalidToken):
        p.encryptor.decrypt(alice_raw.text, "bob")
