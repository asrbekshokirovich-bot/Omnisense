# Omnisense — Dispatch Continuation Prompt

*Paste this to a fresh agent/session to continue development. It is self-contained — the
agent will not have the prior conversation. Read the repo docs it points to before coding.*

---

## Your role
You are continuing development of **Omnisense**, an AI **personal-memory** product for
**Uzbekistan**: a cheap wearable + app that records conversations/meetings and lets the user
ask anything later (and get a morning briefing), working in **Uzbek and Russian**. You are
picking up a working **Phase 0** codebase. Develop on branch **`claude/great-ptolemy-Nbfax`**,
commit with clear messages, **push to that branch**, and keep the existing **draft PR #1**
updated. Repo scope is `asrbekshokirovich-bot/Omnisense` (use the GitHub MCP tools, not `gh`).

## Read these first (in the repo)
- `README.md` — overview + how to run Phase 0.
- `docs/business-plan.md` — model (hardware at cost + subscription, 3 months free),
  Uzbekistan pricing/economics, the raise.
- `docs/development-plan.md` — **architecture, tech stack, residency split, the pipeline,
  the Uzbek-STT workstream, phased delivery.** This is your technical north star.
- `docs/demo-sprint.md` — the 30-day investor-demo scope.
- `docs/market-research.md` — competitive landscape + sources.
(Visual versions: `docs/omnisense-report.html`, `docs/development-plan.html`.)

## Locked product/strategy decisions (do not relitigate)
- **Software-first, audio-first.** First use case = **conversation/meeting memory**. Vision
  ("find my keys", "show-me-how") is later.
- **Entry device = cheap audio pendant** (off-the-shelf for the demo — no custom hardware
  yet); **glasses** are a later premium tier.
- **Business model:** sell hardware **at cost**, all revenue from **subscription**, first
  **3 months free**, **annual prepay + card-on-file** trial. Pricing (som): Personal ~$2,
  Pro ~$4, Business ~$10–16/seat. Payments via **Payme/Click** + carrier billing + BNPL.
- **The moat:** a **self-hosted, fine-tuned Uzbek/Russian speech-to-text model served
  in-country (Tashkent)** — solves cost, data-residency law, and Uzbek quality at once.
- **Trust positioning:** local-first, encrypted, "your voice data stays in Uzbekistan."
- **Go-to-market:** Telegram-first, Uzbek + Russian.

## Current state — what's built & verified
Phase-0 thin loop (`capture → transcribe → remember → answer → brief`) is implemented and
runs **fully offline** (mock providers + in-memory store).
- `backend/` — FastAPI app (`/ingest/text`, `/ingest/audio`, `/ask`, `/briefing`,
  `/sessions`, `DELETE /data`); `app/pipeline.py` orchestrates; **providers behind
  interfaces** (`app/providers`: mock, `yandex_stt`, `llm_openai`, `llm_anthropic`);
  **stores** (`app/store`: in-memory default, `pgvector`); `demo.py`, `ingest_file.py`.
- `ml/eval/` — **WER eval harness** (`run_eval.py`, `wer.py`) — the Uzbek/Russian accuracy
  gate. `infra/` — docker-compose (pgvector + Redis + API). `mobile/` — Flutter shell with a
  record-and-upload capture screen. `web-demo/` — browser client.
- **Tests pass: `cd backend && python -m pytest -q` → 14 passed, 1 skipped** (pgvector skips
  without `TEST_DATABASE_URL`). Provider adapters are unit-tested with the HTTP layer mocked.
- **Live-verified:** the **Anthropic/Claude** answer+briefing path, end to end in Uzbek,
  Russian, and English (set `OMNI_LLM=anthropic` + `ANTHROPIC_API_KEY`).
- **Config** auto-loads a gitignored `backend/.env` (stdlib; see `app/config.py`).

## Environment constraints (important — this sandbox)
- Outbound network uses an **allowlist**: **Anthropic is reachable**; **OpenAI, Yandex,
  HuggingFace are blocked** ("Host not in allowlist"). So you can live-test the Claude path
  here, but **Yandex STT, OpenAI, and HF model downloads must be run/validated in the team's
  own environment**. Don't burn time trying to reach blocked hosts.
- **No Docker daemon** and **no Flutter SDK** here (`docker compose` CLI exists but daemon is
  down; `psql`/`pg_config` exist but no running Postgres). So pgvector-via-Docker and the
  Flutter app compile/run on the team side. Write the code correctly and unit-test what you
  can offline; state clearly what you could not verify here.
- `pip install` works.

## Guardrails
- **Never commit secrets.** `.env` is gitignored and auto-loaded; keep keys only there.
  If a key is shared in chat, tell the user to rotate it.
- **Privacy by construction:** default-OFF capture, one-tap delete, encrypt at rest/in
  transit, and the **residency split** — raw audio + **voiceprints (biometric)** + STT stay
  in-country; only derived **text** may go to an external LLM, with consent. (See dev plan §1.)
- **Keep tests green** before every commit (`python -m pytest -q` from `backend/`).
- **Providers/stores stay behind their interfaces** so cloud↔self-hosted swaps need no
  pipeline changes. Don't hardcode a vendor.
- Don't over-engineer; match scope to the task. After pushing, ensure PR #1 reflects it.

## Prioritized next tasks (pick top-down; each is a small, shippable PR increment)
1. **Real embeddings behind a self-hostable interface.** The mock embedding is keyword-only,
   so Uzbek semantic recall is weak. Add an `EmbeddingProvider` for **BGE-M3 / multilingual-
   e5** (local sentence-transformers) and/or an OpenAI-compatible endpoint; keep mock as
   fallback; unit-test with mocked HTTP/model. (HF is blocked here — implement + test offline;
   team downloads the model.)
2. **Diarization** ("who said what") — integrate **pyannote** behind a `Diarizer` interface
   with **owner voice enrollment**; this is the quality edge. Mock/stub now, real in team env.
3. **Persistence path:** make the pgvector store first-class; verify the integration test
   (`TEST_DATABASE_URL`) and the docker-compose stack (team env). Add Alembic-style migrations
   if useful.
4. **Yandex STT spike + self-hosted plan:** finalize `ingest_file.py` flow; document running
   the WER eval; scaffold an in-country self-hosted Whisper serving interface (`ml/`).
5. **Auth + multi-tenancy + usage metering** (per-user isolation; tier caps) — needed before
   any beta.
6. **Mobile:** finish record→upload, add consent UI + recording indicator, background-capture
   plan; compile with Flutter (team).
7. **Billing skeleton** (Payme/Click recurring, 3-month trial, annual) — Phase 1.
8. **Knowledge-graph memory** (Graphiti/Mem0) for "what did I commit to / what changed."
9. **Privacy/residency hardening:** encryption at rest, consent log, region feature-gating,
   DB-registration notes.

## Definition of done for Phase 0 (the demo)
A polished loop the investor uses on real meetings: reliable cited recall + a morning
briefing, with **Russian + Uzbek transcription validated** (run the Yandex spike → score with
`ml/eval/run_eval.py`). Keep it Android-first, default-off, deletable.

## First action
1. `cd backend && pip install -r requirements.txt && python -m pytest -q` (confirm green).
2. `python demo.py` to see the loop.
3. Read `docs/development-plan.md`, then start task #1 (real embeddings), commit, push, and
   update PR #1. Report what you verified vs. what needs the team's environment.
