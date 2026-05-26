# Omnisense backend (Phase 0)

The thin loop: **capture → transcribe → remember → answer → brief**, in Uzbek/Russian.
Runs fully **offline** by default (mock providers + in-memory store) — no keys, no infra —
and swaps to real providers (Yandex STT / OpenAI-compatible LLM) and pgvector via env only.

## Run it (offline, ~30 seconds)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload      # http://localhost:8000  (docs at /docs)
```
Or see the loop in the terminal:
```bash
python demo.py
```
Run the tests:
```bash
python -m pytest -q
```

## Endpoints
| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | status + stats + active providers |
| POST | `/ingest/text` | remember a pasted transcript `{text, lang}` |
| POST | `/ingest/audio` | upload audio/file (mock STT reads `.txt` as a transcript) |
| POST | `/ask` | `{question, lang}` → answer + citations |
| GET | `/briefing?lang=` | daily summary: decisions, action items, key quotes |
| GET | `/sessions` | list captures |
| DELETE | `/data` | one-tap delete everything (privacy) |

Quick check:
```bash
curl -s localhost:8000/ingest/text -H 'content-type: application/json' \
  -d '{"text":"We agreed to ship the demo on Friday.","lang":"en"}'
curl -s localhost:8000/ask -H 'content-type: application/json' \
  -d '{"question":"when is the demo?","lang":"en"}'
```

## Going real (set in `.env`, see `.env.example`)
- `OMNI_LLM=anthropic` (+ `ANTHROPIC_API_KEY`) — Claude for answers + briefings (recommended).
- `OMNI_STT=yandex` (+ `YANDEX_API_KEY`, `YANDEX_FOLDER_ID`) — Uzbek/Russian cloud STT.
- `OMNI_EMBED=openai` / `OMNI_LLM=openai` (+ `OPENAI_API_KEY`) — OpenAI-compatible alternative.
  *(Cross-border text path — only with consent; voice stays in-country. See the dev plan.)*
- `OMNI_STORE=pgvector` (+ `DATABASE_URL`) — production store; use `infra/docker-compose.yml`.

### Ingest a file (the Yandex STT spike)
```bash
# offline (reads a .txt transcript):
python ingest_file.py meeting.txt --lang uz --ask "demoni qachon yetkazamiz?"
# real Uzbek/Russian STT:
OMNI_STT=yandex YANDEX_API_KEY=... YANDEX_FOLDER_ID=... python ingest_file.py meeting.ogg --lang uz
```
Then score transcription quality with `../ml/eval/run_eval.py`.

### Tests
`python -m pytest -q` runs the loop tests, the API tests, and **provider unit tests**
(Yandex/OpenAI/Anthropic request+parse, with the HTTP layer mocked — no keys needed). The
pgvector integration test runs only when `TEST_DATABASE_URL` is set.

## Design
Providers and the store sit behind interfaces (`app/providers`, `app/store`), so the same
`app/pipeline.py` runs offline for the demo and in production (self-hosted, in-country STT +
pgvector) without code changes. See [`../docs/development-plan.md`](../docs/development-plan.md).
