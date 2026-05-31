# infra — local production-like stack

Local **pgvector + Redis + API** mirror of production, for the team to exercise the
real-Postgres path that the offline demo doesn't touch. The offline demo and the
backend test suite do **not** need this — the backend defaults to an in-memory store
and mock providers, and an in-memory `psycopg` fake covers the SQL shape of the
pgvector store in CI (`tests/test_pgvector_offline.py`, 7 tests). This stack is for:

1. Running the real pgvector integration test
   (`backend/tests/test_pgvector.py`, skipped without `TEST_DATABASE_URL`).
2. Demoing the API against real persistence (so memory survives a restart).
3. Exercising real provider paths (Yandex / Anthropic / local BGE-M3) end-to-end with
   the corresponding env vars set.

## Bring it up

```bash
docker compose -f infra/docker-compose.yml up --build
# API on http://localhost:8000  with OMNI_STORE=pgvector
```

That command:

- Starts `pgvector/pgvector:pg16` with healthcheck (the `api` waits for it).
- Starts `redis:7-alpine` (room for rate-limit / job queue work in Phase 1).
- Builds the API image from `../backend` and runs it with `OMNI_STORE=pgvector` and
  `DATABASE_URL=postgresql://omni:omni@db:5432/omni`.

On first boot the API runs the schema migrations
(`backend/app/store/_pg_migrations.py`): currently v1 (initial schema) + v2 (tenancy +
metadata indexes). `SELECT * FROM schema_migrations` is the single source of truth for
"what shape is this DB in right now?" — useful when investigating a state mismatch.

## Run the real integration test against the stack

```bash
# In one terminal:
docker compose -f infra/docker-compose.yml up db

# In another:
cd backend
TEST_DATABASE_URL=postgresql://omni:omni@localhost:5432/omni python -m pytest tests/test_pgvector.py -v
```

Each test wipes its tenants on entry — runnable repeatedly without `docker compose down`.

## Inspect / wipe / reset

```bash
# Open a psql shell against the live db.
docker compose -f infra/docker-compose.yml exec db psql -U omni -d omni

# Inside psql:
SELECT * FROM schema_migrations;
SELECT count(*) FROM segments GROUP BY tenant_id;
SELECT count(*) FROM sessions;

# Full reset (drops the volume — loses ALL data):
docker compose -f infra/docker-compose.yml down -v
```

## Wiring real providers (team env only)

Set the relevant env vars in the `api` service of `docker-compose.yml`. Remember to:

- Mount `backend/.env` if you want config to come from there:
  ```yaml
  volumes:
    - ../backend/.env:/app/.env:ro
  ```
- For `OMNI_LLM=anthropic`: `ANTHROPIC_API_KEY` (cross-border — grant the tenant's
  `cross_border_llm` consent first, or every `/ask` returns HTTP 451).
- For `OMNI_STT=yandex`: `YANDEX_API_KEY`, `YANDEX_FOLDER_ID` (also cross-border —
  needs `cross_border_stt` consent).
- For `OMNI_EMBED=local` (BGE-M3 in-country): the image needs `sentence-transformers`
  installed (currently kept out of the base requirements; uncomment the line in
  `backend/requirements.txt` once the team is ready to pay the install cost).
- For `OMNI_DIARIZER=pyannote`: `HF_TOKEN` with access to the gated
  `pyannote/speaker-diarization-3.1` and `pyannote/embedding` models.

## Production note

Voice / voiceprints / database must be hosted **in Uzbekistan** (Personal-Data Law
ZRU-547, plus IT-Park residency rules). Derived text may call external LLMs only with
consent. Full residency map: [`../docs/data-residency.md`](../docs/data-residency.md).

The `OMNI_LLM=anthropic` / `OMNI_STT=yandex` paths are cross-border by design and are
guarded by the per-tenant consent log + region gate (`backend/app/consent.py`,
`backend/app/pipeline.py`). See also
[`../docs/development-plan.md`](../docs/development-plan.md) §1 and §9.
