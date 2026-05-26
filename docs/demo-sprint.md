# Omnisense — 30-Day Investor Demo Sprint

> **Goal:** in ~4 weeks, build a working product the **investor can use for several
> real days** and not want to give back — so he commits the ~$1M. Not a product launch;
> a *conviction machine*.

**Scope decisions (locked with you):**
- Entry device = **cheap audio pendant** (off-the-shelf, not custom).
- Use case = **conversation/meeting memory** only (Pillar 1). No vision, no screen.
- Built by your **existing IT team**. Software-first.
- Market = **Uzbekistan** → the demo must work in **Russian and Uzbek**.

**The one feeling to manufacture:** *"I had a meeting, and the next morning Omnisense
told me exactly what I agreed to — and I asked it a question and it answered, in my
language, with the exact quote."*

---

## What's IN vs OUT (ruthless scope)

| IN (must work) | OUT (after funding) |
|---|---|
| Record a conversation (pendant or phone) | Custom hardware / industrial design |
| Transcribe **Russian + Uzbek** | Vision: keys / show-me-how |
| Identify speakers ("who said what") | Screen/PC memory |
| Searchable memory + **ask anything** (cited answers) | Real billing / payments |
| **Morning briefing** (decisions, action items) | App-store polish, onboarding flows |
| Privacy basics: encrypted, one-tap delete, default-off | Scale, multi-tenant infra |
| Clean, simple UI in Russian/Uzbek | Teams/business features |

If something isn't on the "IN" list, don't build it this month.

---

## Hardware for the demo (buy, don't build)
Pick the fastest path that *feels* like a wearable:
- **Best:** an **off-the-shelf open pendant (Omi, ~$70–89)** — looks/feels like the
  real product, you control the audio stream.
- **Fallback:** a **cheap Bluetooth clip-on/lavalier mic + the phone** in a pocket — even
  simpler, totally fine for a demo.
- **Backup:** phone mic alone.
> The investor is judging the *experience*, not the plastic. Spend the month on software.

---

## Recommended demo stack (optimized for speed, not scale)
- **App:** a simple **mobile app** (or even a web app + phone recorder) — record, a
  timeline, an "ask" box, and the morning briefing. Keep it to a few screens.
- **Capture:** record audio, run **silence detection (VAD)** so you only process speech.
- **Transcription + speaker ID:** for the demo, use a **cloud speech-to-text that handles
  Russian well** (Russian is well-supported) and the **best available Uzbek** option
  (this is the key technical unknown — see the language note; the research pass will name
  the best provider/model for Uzbek). On-device transcription is the *production* cost
  lever — **don't block the demo on it.**
- **Memory:** **Postgres + pgvector** (one database for text, vectors, time, speaker).
- **Assistant:** a **frontier LLM** (Claude / GPT / Gemini) doing retrieval over the
  memory, **answering in Russian/Uzbek** with citations.
- **Privacy (visible):** encrypt stored data, a real **delete** button, recording is
  **off until you start it**. The investor should *see* this.

> Language is the make-or-break detail for an Uzbek demo: confirm the Russian/Uzbek
> transcription quality in **Week 1** on real local audio. If Uzbek STT is weak, demo
> primarily in **Russian** first and treat strong **Uzbek** as the funded R&D goal (it's
> also your local moat).

---

## Week-by-week plan

### Week 1 — Capture → transcript (the foundation)
- Choose & set up the demo hardware; get audio reliably into the app.
- Wire up **VAD + cloud STT + speaker diarization**; produce a clean, timestamped,
  speaker-labeled transcript.
- **Test Russian AND Uzbek on real recordings** — this is the critical early risk check.
- **End of week:** record a real 20-minute conversation → get a readable transcript with
  speakers.

### Week 2 — Memory → ask anything (the magic)
- Chunk transcripts, create embeddings, store in pgvector with time + speaker metadata.
- Build the **"ask" experience:** natural-language question → retrieve → LLM answers
  **in the user's language with citations** ("at 14:12 you said…").
- **End of week:** ask "what did we decide about X?" and get a correct, cited answer.

### Week 3 — Morning briefing + UI + privacy (the "wow" + the trust)
- Generate a **daily briefing**: decisions, commitments/action items, key quotes.
- Build the **simple UI** (timeline, ask box, briefing) in Russian/Uzbek.
- Add visible **privacy**: encryption, one-tap delete, default-off, a recording indicator.
- **End of week:** a full loop — record a day → next-morning briefing → ask follow-ups.

### Week 4 — Make it real on the investor (the close)
- **Reliability + accuracy pass** — especially **speaker ID** and **Uzbek/Russian**
  transcription (the things he'll notice).
- **Put it on the investor** for several real days on his own meetings.
- **Instrument usage** so you can show him *his own* value (meetings captured, questions
  answered, time saved).
- Prepare the **pitch**: this product + the [`business-plan.md`](./business-plan.md) +
  a one-screen metrics view.
- **End of week:** the ask.

---

## Success criteria (how you know the demo "won")
- The investor **uses it unprompted** for 3+ days.
- He successfully **asks it about his own conversations** and trusts the answers.
- The **morning briefing** genuinely saves him effort.
- He says some version of **"I'd keep using this"** — that's the green light for the ~$1M.

---

## Risks specific to a 1-month timeline
| Risk | Mitigation |
|---|---|
| **Uzbek transcription is weak** | Validate Week 1; demo in Russian first if needed; make Uzbek the funded R&D moat |
| **Diarization errors undercut trust** | Pick the strongest available diarization; let the user correct/label speakers in the demo |
| **Scope creep** | Hold the IN/OUT line above; the briefing + cited recall is enough to win |
| **Hardware fiddliness** | Use the phone + a cheap mic if the pendant integration is slow |
| **Latency feels slow** | Pre-process after the meeting (briefing is async); make *recall* fast |

---

*This sprint feeds **Phase 0** of [`business-plan.md`](./business-plan.md). After the
investor commits, the ~$1M funds real hardware, Uzbek-language R&D, on-device processing
(the margin lever), local payments & data residency, and the private beta.*
