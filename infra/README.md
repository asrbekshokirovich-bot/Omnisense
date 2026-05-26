# infra

Local production-like stack: **pgvector + Redis + the API**.

```bash
docker compose -f infra/docker-compose.yml up --build
# API on http://localhost:8000 with OMNI_STORE=pgvector
```

The offline demo does **not** need this — the backend defaults to an in-memory store and
mock providers. Use this when testing the real persistence path or wiring real providers.

**Production note:** voice/voiceprints and the database must be hosted **in Uzbekistan**
(data-localization law). Derived text may call external LLMs only with consent. See
[`../docs/development-plan.md`](../docs/development-plan.md) §1 (residency split) and §9.
