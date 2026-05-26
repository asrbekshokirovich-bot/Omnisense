# Omnisense

**A 24/7 "second brain."** A wearable + software system that listens, watches, and
remembers your life so you can ask it anything later — what was decided in a meeting,
where you left your keys, or how you fixed something last time.

> Status: **Phase 0** — runnable thin loop with the full provider matrix (mock /
> Anthropic / Yandex / pyannote / BGE-M3 / pgvector), multi-tenancy, consent log +
> region gate, owner-voice enrollment, billing skeleton. 71 backend tests + 6 eval
> tests pass. See **[`backend/`](backend/)**.
>
> Launch market: **Uzbekistan.** Model: **hardware at cost + subscription, first 3
> months free.** Moat: **in-country, fine-tuned Uzbek speech** that Big Tech won't build.

## Start here
- **[`docs/business-plan.md`](docs/business-plan.md)** — the complete business plan,
  localized for Uzbekistan (pricing in som, unit economics, the ~$1M raise, GTM,
  roadmap, data-law/IT-Park). **Primary doc.**
- **[`docs/omnisense-report.html`](docs/omnisense-report.html)** — the visual,
  investor-friendly brief (open in any browser; self-contained).
- **[`docs/demo-sprint.md`](docs/demo-sprint.md)** — the 30-day plan to build the
  investor demo.
- **[`docs/development-plan.md`](docs/development-plan.md)** — the engineering plan:
  architecture, tech stack, the Uzbek-speech workstream, pipeline, and delivery phases.
- **[`docs/mobile-background-capture.md`](docs/mobile-background-capture.md)** — the
  Phase 1 plan for background recording (foreground service + VAD + encrypted buffer
  + deferred upload; iOS audio background; BLE pendant).
- **[`docs/master-plan.md`](docs/master-plan.md)** — the product & technical build
  plan (vision, architecture, privacy, next steps).
- **[`docs/market-research.md`](docs/market-research.md)** — the global competitive
  landscape and lessons (Humane, Rabbit, PLAUD, Limitless, Bee, Meta Ray-Ban) with
  sources.

## The approach in one breath
Software-first, audio-first. Prove the memory + recall engine on hardware you can buy
today; start with **conversation/meeting memory** (the proven sticky use case); add
vision ("find my keys", "show me how") later; treat **glasses** as the eventual
north-star device. **Sell hardware at cost and earn all revenue from a subscription**
(first 3 months free) — the model that built Oura (~$11B) and Whoop (~$10.1B). Win on
**trust** — local-first, encrypted — because Big Tech already owns the big memory
wearables and can't be out-scaled, only out-trusted.

## The four pillars (use cases)
1. **Conversation & meeting memory** — "What did we agree to ship by Friday?" *(MVP)*
2. **Screen / digital memory** — "What was that link I saw yesterday?" *(early add-on)*
3. **Find-my-things** — "Where did I last see my keys?" *(needs a camera — Phase 2)*
4. **Show-me-how** — "How did I do this last time?" *(hardest — Phase 3)*

## Code — Phase 0 thin loop
The runnable skeleton of capture → transcribe → diarize → chunk → embed → store →
ask → brief. Works **offline** (mock providers + in-memory store), swaps to real
providers (Yandex STT / BGE-M3 / Anthropic / pyannote / pgvector) via env only.

```bash
cd backend
pip install -r requirements.txt
python demo.py                  # see the loop end-to-end in the terminal
uvicorn app.main:app --reload   # API on :8000 (open web-demo/index.html to use it)
python -m pytest -q             # 71 passed, 1 skipped
```

What's wired:
- **STT:** mock | Yandex SpeechKit (RU/UZ; short sync + long async + speaker labels).
- **Embeddings:** mock | `local` (sentence-transformers / BGE-M3 in-country) |
  OpenAI-compatible (works against cloud OpenAI *or* a self-hosted vLLM/TEI/Ollama
  gateway in Tashkent).
- **LLM:** mock | Anthropic (Claude Haiku) | OpenAI-compatible. Cross-border calls
  are gated on per-tenant consent (HTTP 451 if missing).
- **Diarizer:** off | mock | pyannote-audio (in-country); per-tenant owner-voice
  enrollment maps "SPEAKER_00" → "owner" for the meeting-recall UX.
- **Store:** in-memory | pgvector (production; sized to the embedder's actual dim,
  tenant-aware, with metadata filters and a startup dim-mismatch guard).
- **Billing:** mock | Payme / Click adapter stubs (fill in with the merchant
  contract); 90-day trial + plan catalog in som; full /start-trial → /subscribe →
  /webhook flow.

Privacy:
- **Default-OFF capture** — the server records nothing without an explicit /ingest.
- **Multi-tenancy** via `X-User-Id`; one-tap `DELETE /data` and `DELETE /sessions/{id}`.
- **Per-tenant consent log** — append-only audit trail for ZRU-547; controls the
  region gate that refuses cross-border LLM/STT without consent.
- **Owner voiceprints** stay in-country and never reach the LLM.

```
backend/    FastAPI loop, providers (mock/Yandex/Anthropic/OpenAI/pyannote/BGE-M3),
            in-memory + pgvector stores, consent log, billing, tests.
ml/         Uzbek/Russian WER + CER eval harness; provider comparison; JSON output.
infra/      docker-compose (pgvector + Redis + API).
mobile/     Flutter shell (Capture / Ask / Briefing / Settings) with consent gate,
            recording indicator, per-install tenant identity, one-tap delete.
web-demo/   Throwaway browser client to drive the API.
```

## Next step
Phase 0 continues: validate **Yandex SpeechKit** Russian + Uzbek accuracy on real
audio (`OMNI_STT=yandex`, then score with `ml/eval/run_eval.py`), exercise the
`local` BGE-M3 embedder against real weights, and ship the mobile background-capture
plan. See [`docs/development-plan.md`](docs/development-plan.md) §13.
