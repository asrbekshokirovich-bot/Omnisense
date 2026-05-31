# Data residency map

Where every category of Omnisense user data **lives**, who can read it, and whether it
**crosses the Uzbekistan border**. Drives the consent gate (`backend/app/consent.py`),
the region check inside `Pipeline._require_consent_for_*`, and the eventual
**IT-Park data-localization registration** that the business plan calls for.

This is the regulator-facing artifact for **Personal-Data Law ZRU-547 (2 July 2019)**.
Update it whenever you add a new piece of user data or a new provider — the law treats
the *categories* of data, not specific tables, so a missed entry here is the gap.

> Phase 0 ships the residency *enforcement* and the *audit artifacts*; the actual
> Uzbekistan hosting of Postgres + STT happens in Phase 1 once the IT-Park residency
> contract is signed. The split below describes the Phase-1 production architecture
> that the code already supports today.

## Categories

| # | Category | At rest in | Encrypted at rest? | Crosses border? | Consent scope | Notes |
|---|----------|-----------|-------------------|----------------|---------------|-------|
| 1 | Raw audio (uploaded clips, future BLE pendant stream) | Uzbekistan only — backend disk / S3-equivalent | App-level (Phase 1 — Fernet/KMS envelope) + disk-level | **Never** | `recording` | Voice = biometric under ZRU-547. Source of every other category below. |
| 2 | Voiceprints — owner enrollment centroid + per-turn diarization vectors | Uzbekistan only — `<base>.<tenant>.json` (current Phase 0 path) → Postgres BYTEA (Phase 1) | App-level Fernet (Phase-1 wiring — same Encryptor that already covers segment text) | **Never** | `recording` | Treated as biometric. The voiceprint never leaves the diarizer process; the LLM never sees it. |
| 3 | Transcript text (segments) | Uzbekistan — pgvector / Postgres | **Yes — Fernet per-tenant DEK from server KEK (`OMNI_ENCRYPTION=fernet`)** | Sent to cross-border LLM ONLY for the specific /ask or /briefing call that the user authorizes | `cross_border_llm` | Embeddings (vectors) are computed before encryption and stay alongside the ciphertext. Search uses vectors, not text. |
| 4 | Embeddings | Uzbekistan — pgvector | Not yet; encrypting kills HNSW search semantics. Phase-2 review with the team. | **Never** | implicit (via `recording`) | Reversal attacks on text embeddings are an open research area. We treat them as quasi-PII and never export. |
| 5 | LLM-derived answers + daily briefings | Computed cross-border (when `cross_border_llm` consented), then stored in Uzbekistan | App-level Fernet (Phase 1) | Generated abroad; result stored locally | `cross_border_llm` | Only the question + top-K cited text excerpts leave; full memory does not. |
| 6 | Consent log (audit trail) | Uzbekistan — `consent.<tenant>.json` (Phase 0) → Postgres (Phase 1) | Plaintext (integrity > confidentiality for the audit log; tamper-evident via Postgres + WAL is enough) | **Never** | n/a | Append-only. Regulators get to read it on demand. |
| 7 | Usage counters | Uzbekistan — in-memory (Phase 0) → Postgres (Phase 1) | Plaintext (just integers) | **Never** | n/a | Drives billing + quota only. |
| 8 | Subscription state | Uzbekistan — in-memory (Phase 0) → Postgres (Phase 1) | Plaintext | **Never** | n/a | Cross-border to Payme/Click for the payment INTENT only — money, not user data. |
| 9 | API keys | Uzbekistan — sha-256 hash only (plaintext shown once at creation, never persisted) | Hashing IS the encryption (one-way) | **Never** | n/a | Tenant-scoped revoke. Compromise scope is one key, not one tenant. |
| 10 | Tenant id (`X-User-Id` or derived from `X-API-Key`) | Uzbekistan | Plaintext (it's the routing key) | Travels with every API call from the mobile app | n/a | Not PII per ZRU-547 (random per-install id, no email / phone). |
| 11 | Request IDs (log correlation) | Uzbekistan (logs) | n/a | Echoed back to clients via `X-Request-Id` | n/a | Not PII. |
| 12 | Cross-border STT (Yandex) input — raw audio | Crosses to Yandex (Russia) when `OMNI_STT=yandex` | Yandex side: their problem (their TLS in transit, their disk at rest) | **Yes** | `cross_border_stt` | Production: replace with self-hosted Whisper in Tashkent. The Yandex path is the Week-1 risk-check baseline only. |
| 13 | Cross-border LLM (Anthropic / OpenAI) input — question + top-K cited text excerpts | Crosses to Anthropic / OpenAI | Provider side; we only ship what the user authorized | **Yes** | `cross_border_llm` | We do NOT send embeddings, voiceprints, or full memory. The 451 region gate enforces this. |

## Enforcement (where the code lives)

- **Region gate.** `backend/app/pipeline.py::Pipeline._require_consent_for_{llm,stt}`
  raises `ConsentRequired` → HTTP 451 if the configured provider would send data
  abroad and the tenant has not granted the matching scope. The gate is checked at
  the top of `ingest_audio`, `ask`, and `briefing`.
- **Consent log.** `backend/app/consent.py::ConsentLog`. Append-only per tenant.
  `GET /consent` is the regulator-facing endpoint.
- **At-rest encryption.** `backend/app/encryption.py`. Per-tenant DEK derived via
  HKDF-SHA256 from a server-held KEK; Fernet AEAD. Tenant DEKs are deterministic
  from the KEK so restarts never lose access — the KEK is the only secret that
  must be persisted (production = Vault / KMS).
- **Tenant isolation in the store.** Every read takes a `tenant_id`; the integration
  test (`backend/tests/test_pgvector.py`) and the offline fake
  (`backend/tests/test_pgvector_offline.py`) both verify that wrong-tenant access
  returns nothing — even the cross-tenant delete-session call is a no-op.
- **Privacy operations bypass the rate limiter.** `DELETE /data` and `DELETE
  /sessions/{id}` never wait for a token — "delete me" is a right under
  ZRU-547 Art. 24.

## What is NOT in scope here

- Logs and metrics from external observability tools (DataDog, Sentry, etc.) — when
  the team wires those, they MUST be the in-country offerings or set to drop request
  bodies / arguments. Track separately.
- The `Auto-load backend/.env` behavior reads from a local file by design. The file
  is gitignored (`.gitignore` line 10). KEKs in production come from Vault, never
  from `.env`.
- iOS / Android device-local data (the consent file, tenant id, mobile-only state
  before upload) — covered by platform Data Protection (iOS) / Keystore (Android)
  in Phase 1's background-capture work. See `docs/mobile-background-capture.md`.

## Migration path to true in-country production

1. **Postgres in Tashkent** — the same `pgvector/pgvector:pg16` image, IT-Park hosted.
   Migrations from `backend/app/store/_pg_migrations.py` apply on first connect.
2. **KEK in Vault / Yandex Cloud KMS (in-country)** — replace `OMNI_KEK=…` with a
   secret fetched at startup. The Encryptor interface does not change.
3. **Self-hosted Whisper for STT** — drop `OMNI_STT=yandex` and the
   `cross_border_stt` scope becomes vestigial. Voice never crosses.
4. **Keep `cross_border_llm` opt-in** — the LLM call is the only data path that
   crosses the border in steady state. Users that say "no" still get the mock LLM
   summarizer (or the local-LLM path, when it exists).

## Adjacent surveillance vectors

The categories above describe data Omnisense *creates and stores*. They do not
address data the environment *generates about the user* independently of Omnisense.
The most relevant adjacent vector today is **Wi-Fi sensing** — the 2025 KIT/KASTEL
work and the IEEE 802.11bf standard showed that the unencrypted Beam-Forming
Feedback (BFI) emitted by every modern router can be turned into a per-person RF
gait signature with seconds of observation. See
[`docs/wifi-sensing-research.md`](wifi-sensing-research.md) for the full report,
threat model, and Phase-3 pilot plan. The honest framing for Omnisense's privacy
positioning: Omnisense does not capture audio without your consent, but your
physical presence is detectable by other systems regardless of what Omnisense does,
and "your voice data stays in Uzbekistan" does not guarantee that your RF identity
isn't already in a foreign cloud dataset gathered by some hotel or airport router.
We track this category but do not yet defend against it; the C1 ("RF-surveillance
detection") tier in the research doc is the defensive feature we may build later.
