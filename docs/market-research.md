# Omnisense — Market Research (AI Wearables & Memory Devices)

> Competitive landscape and lessons as of **May 2026**, gathered from web research.
> This is the evidence base for [`master-plan.md`](./master-plan.md).
> **Caveat:** several figures come from press/secondary sources and are flagged where
> uncertain. Verify the high-stakes ones (sales, valuations, legal specifics) before
> relying on them.

---

## 1. The graveyard — standalone AI gadgets that failed

### Humane AI Pin — the canonical flop
- $699 screenless clip-on + **$24/mo** (own cellular line); ~$230M raised, ex-Apple founders.
- 13MP camera, laser "ink" palm projector; **battery only ~2–4 hrs**, overheated.
- Pitched as a **phone replacement**; in reality slow, wrong answers, couldn't reliably
  do basics, no app integration. MKBHD: *"The Worst Product I've Ever Reviewed."*
- ~10,000 units; **returns outpaced sales** by Aug 2024. **HP bought assets for ~$116M
  (Feb 2025)**; the Pin was **bricked at noon PST Feb 28, 2025** — dead hardware.
- **Lesson:** don't replace the phone; battery/heat are existential; never brick users.

### Rabbit R1 — "Large Action Model" that was largely an app
- $199 handheld (Teenage Engineering design); ~$10M preorders, ~100k+ units.
- The "LAM" was effectively an **LLM + browser automation + hardcoded scripts**; the
  whole experience **ran as an Android app** that could be sideloaded onto a phone.
- **Hardcoded API keys** leaked (June 2024). Engadget: *"a $199 AI toy that fails at
  almost everything."* Only ~5,000 of ~100k buyers active (Sept 2024).
- **Lesson:** if it can be an app, it will be; don't overpromise; ship secure.

### Friend — the companion necklace and the backlash
- $99–129 always-listening "emotional companion"; ~$7M raised; **$1.8M for friend.com**.
- ~$1M NYC subway ad blitz, **heavily vandalized**; became the face of the anti-AI/
  surveillance backlash. Reviews scathing (~7–10s latency, condescending replies).
- **Lesson:** always-listening + emotional framing triggers fierce public hostility.

---

## 2. The audio-memory category (closest to Omnisense)

| Device | Price | Model | Status / signal |
|---|---|---|---|
| **PLAUD** (Note / NotePin) | ~$159 | **Tap-to-record** meetings → cloud summary | **Category winner, 1M+ units;** ~$250M 2025 rev (reported) |
| **Limitless Pendant** | $99 + ~$19/mo | Always-on, best consent UX | **Acquired by Meta, Dec 2025** |
| **Bee** | $50 + ~$19/mo | Always-on wristband | **Acquired by Amazon, Jul 2025** |
| **Friend** | $99–129 | Always-on companion | Backlash; "Museum of Failure" |
| **Omi / Based Hardware** | ~$70–89 | **Open-source**, dev-focused | Best **DIY starting point** (MIT PCB+firmware) |

**What works:** summaries/action items > raw transcripts; tap-to-record + meetings
(PLAUD) is stickier and more consent-friendly than ambient life-logging; routing to
frontier models gives ~90–98% accuracy in clean audio.

**Where they all fall short:**
- **Speaker diarization** ("who said what") is the **universal weak point** — wrong/
  duplicated labels, manual cleanup, sometimes failing to recognize the owner. *This is
  the clearest quality opportunity for a new entrant.*
- Accuracy collapses in noise/accents/multilingual; silent recording failures erode trust.
- **Battery vs. always-on** tension (~6–14 hrs real use).
- **"Novelty then drawer"** churn for ambient/companion devices; meeting-capture sticks.
- **Bystander consent is unsolved** — an LED + a ToS clause is not a social contract.

**Strategic signal:** Meta (Limitless) and Amazon (Bee) **both acquired memory wearables
in H2 2025.** The category is validated *and* about to be commoditized by Big Tech →
a small independent must differentiate on **trust (local-first privacy)** and **focus.**

---

## 3. AI glasses — the winning form factor

- **Meta Ray-Ban (Gen 2, ~$379):** 12MP cam, 3K video, 5-mic array, open-ear audio,
  ~8 hr battery, multimodal "Hey Meta, what am I looking at?", live translation.
  **~7M pairs sold in 2025**; production target 20–30M/yr. The clear category winner.
- **Meta Ray-Ban Display + Neural Band (~$800):** in-lens HUD + an **EMG wristband**
  (read finger muscles for silent control — widely praised). But glasses are thick,
  display tiny (20° FOV), battery ~6 hr and drops fast.
- **Google Android XR + Gemini/Project Astra:** glasses with Warby Parker/Gentle
  Monster, **audio-only shipping ~fall 2026**, display later. Samsung **Galaxy XR**
  headset ($1,800) shipped Oct 2025.
- **Apple:** Vision Pro underperformed (~500–600k lifetime, est.); reportedly pivoting
  to **AI glasses (~2027)**. Visual Intelligence already does camera Q&A on iPhone. *(rumor)*
- **Open/niche:** **Brilliant Labs Frame** ($349, open-source, has camera + SDK) and
  **Even Realities G1** ($599, HUD, no camera) — Frame is the hacker-friendly option.
  Plus many Chinese players (Xiaomi ~$278, Rokid, RayNeo, Solos).

**Why glasses win:** camera at eye level = true first-person view; built-in audio I/O;
socially accepted fashion frames; phone-tethered (offload compute); glanceable display
upside. **This is why Omnisense's north-star device is glasses.**

**Still unsolved:** all-day battery *with* capture; a **trustworthy, tamper-proof
recording indicator** for bystanders; social acceptance of persistent recording.

> ⚠️ **Platform note for builders:** Meta's glasses are a **closed platform** — you
> cannot pipe their camera into a third-party "second brain" app. For DIY vision,
> use **open hardware** (Omi Glass, Brilliant Labs Frame) or the phone.

---

## 4. Screen-memory software + the privacy/legal landscape

### Microsoft Recall — the cautionary tale
- Screenshots your PC every few seconds → searchable timeline. The 2024 version stored
  snapshots in an **unencrypted database**; researchers extracted "the last three months
  of everything you typed and viewed" (the "TotalRecall" tool). UK ICO inquiry; pulled.
- Rebuilt: **opt-in, off by default**, AES-256 encryption, TPM-backed keys, Windows
  Hello gating, sensitive-content filtering, retention controls. GA ~April 2025.
- **Lessons:** **default-off**, **local storage ≠ security**, encrypt + gate access.
- Open-source local-first alternative: **screenpipe** (MIT) — good for the Pillar-2 build.

### Legal landscape (US + EU) — *research synthesis, not legal advice*
- **US wiretapping:** federal baseline is **one-party consent**, but **~11–12 states
  require all-party consent** (California, Connecticut, Delaware, Florida, Illinois,
  Maryland, Massachusetts, Michigan, Montana, Nevada, New Hampshire, Pennsylvania,
  Washington — lists vary). Recording non-consenting people there → criminal + civil risk.
- **Illinois BIPA:** voiceprints & faceprints = **biometric identifiers**; informed
  written consent + retention/destruction policy required; **private right of action**
  ($1,000–5,000/violation) → class-action magnet.
- **GDPR (EU):** recording identifiable strangers = you are a **data controller**; the
  "household exemption" does **not** cover capturing third parties in public (*Ryneš*,
  C-212/13). Full obligations: lawful basis, transparency, access/erasure.
- **EU AI Act:** **emotion recognition** (workplace/education) and **biometric
  categorization** are **prohibited** (in force Feb 2, 2025; fines up to €35M / 7%).
  Transparency duties from Aug 2, 2026. **Do not build mood/emotion features.**

### Privacy & security design requirements (checklist)
Default-OFF · on-device-by-default · encrypt everywhere (AES-256/TLS, hardware keys) ·
hard-to-defeat recording indicator · bystander consent via owner-voice gating · data
minimization & sensitive-content filtering · short retention + one-tap deletion ·
regional feature-gating (all-party states, EU) · no secrets in client code · breach
readiness. *(See master plan §6 for the full list.)*

---

## 5. Enabling technology (May 2026)

- **Speech-to-text:** edge — **faster-whisper / distil-whisper** (run on phone);
  cloud — **Soniox / Deepgram Nova-3 / AssemblyAI** (best accuracy, bundled diarization,
  ~$0.12–0.45/hr).
- **Diarization (the quality battle):** **pyannote 3.1** (open), **NVIDIA NeMo
  Sortformer** (more accurate); cloud APIs improving in noise.
- **VAD / wake-word:** **Silero VAD**, **Picovoice Porcupine** (runs on MCUs).
- **Vision:** on-device **Moondream / SmolVLM / Qwen2.5-VL-3B**; cloud **Gemini Flash /
  GPT-mini / Claude Haiku** for OCR + reasoning.
- **Memory store:** **pgvector** (MVP — vectors + metadata + time filters in Postgres) →
  **Qdrant** at scale; **hybrid** dense+keyword retrieval.
- **Agent memory:** **Mem0** (pragmatic), **Graphiti/Zep** (temporal knowledge graph for
  "what changed when"), **Letta/MemGPT** (paged context). Episodic + semantic split; roll
  up/decay old data.
- **Wearable hardware (if/when you build):** **Omi / Based Hardware** is fully
  **open-source** (nRF5340 pendant + ESP32-S3 glasses, PCB/BOM/firmware) — the best
  starting point. **Battery is the #1 bottleneck** (~10–14 hr audio; video collapses it).
- **The brain:** a frontier LLM (Claude / GPT / Gemini) doing **RAG** over the memory
  with tool-calls (filter by time/person/location).

**Hardest bottlenecks, ranked:** (1) battery/always-on power, (2) diarization accuracy,
(3) round-trip latency, (4) 24/7 storage & compute cost, (5) privacy/consent.

---

## Sources

A representative set (full lists were gathered during research; many primary pages
blocked automated fetching, so some details are cross-checked search summaries).

**Failed devices:**
- HP buys Humane assets for $116M — TechCrunch: https://techcrunch.com/2025/02/18/humanes-ai-pin-is-dead-as-hp-buys-startups-assets-for-116m/
- Humane returns outpace sales — 9to5Mac: https://9to5mac.com/2024/08/07/humane-ai-pin-woes-worsen-as-recent-returns-exceed-sales/
- Rabbit R1 review — Engadget: https://www.engadget.com/rabbit-r1-review-a-199-ai-toy-that-fails-at-almost-everything-161043050.html
- Rabbit r1 — Wikipedia: https://en.wikipedia.org/wiki/Rabbit_r1
- Friend AI backlash — CNN: https://www.cnn.com/2025/11/16/tech/friend-ai-device-backlash-ceo-avi-schiffmann

**Audio-memory wearables:**
- Meta acquires Limitless — TechCrunch: https://techcrunch.com/2025/12/05/meta-acquires-ai-device-startup-limitless/
- Amazon acquires Bee — TechCrunch: https://techcrunch.com/2025/07/22/amazon-acquires-bee-the-ai-wearable-that-records-everything-you-say/
- I tried Amazon's Bee — TechCrunch (May 2026): https://techcrunch.com/2026/05/24/i-tried-amazons-bee-wearable-and-am-both-intrigued-and-slightly-creeped-out/
- Limitless consent docs: https://help.limitless.ai/en/articles/10540861-how-to-ask-for-consent-and-let-others-know-you-are-recording
- PLAUD: https://www.plaud.ai/  · Omi (open source): https://github.com/BasedHardware/omi

**Glasses:**
- Ray-Ban Meta Gen 2 — Meta Newsroom: https://about.fb.com/news/2025/09/ray-ban-meta-gen-2-better-battery-life-video-capture/
- Ray-Ban Meta Display + Neural Band: https://about.fb.com/news/2025/09/meta-ray-ban-display-ai-glasses-emg-wristband/
- Android XR glasses (I/O 2026) — Google: https://blog.google/products-and-platforms/platforms/android/android-xr-io-2026/
- Brilliant Labs Frame: https://brilliant.xyz/products/frame
- EFF on Meta Ray-Bans / privacy: https://www.eff.org/deeplinks/2026/03/think-twice-buying-or-using-metas-ray-bans

**Screen memory + privacy/legal:**
- Microsoft Recall security architecture — Windows blog: https://blogs.windows.com/windowsexperience/2024/09/27/update-on-recall-security-and-privacy-architecture/
- Recall still allows extraction (contested) — CSO Online: https://www.csoonline.com/article/4159643/microsofts-windows-recall-still-allows-silent-data-extraction.html
- screenpipe (open source): https://github.com/screenpipe/screenpipe
- Recording-consent state survey — Justia: https://www.justia.com/50-state-surveys/recording-phone-calls-and-conversations/
- EU AI Act Article 5 (prohibitions): https://artificialintelligenceact.eu/article/5/
- GDPR household exemption / Ryneš — Hogan Lovells: https://www.hoganlovells.com/en/publications/cctv-cjeu-narrows-the-scope-of-the-household-exemption

**Enabling tech:**
- Open ASR Leaderboard — HuggingFace: https://huggingface.co/blog/open-asr-leaderboard
- Diarization libraries/APIs 2026 — AssemblyAI: https://www.assemblyai.com/blog/top-speaker-diarization-libraries-and-apis
- State of AI agent memory 2026 — Mem0: https://mem0.ai/blog/state-of-ai-agent-memory-2026
- Vector DB benchmarks 2026: https://callsphere.ai/blog/vector-database-benchmarks-2026-pgvector-qdrant-weaviate-milvus-lancedb
- SmolVLM — HuggingFace: https://huggingface.co/blog/smolvlm

> Uncertainty flags worth re-verifying: PLAUD revenue/valuation; Limitless & Bee
> acquisition prices (undisclosed); exact all-party-consent state count (11 vs 12);
> contested 2026 "Recall still leaks" claims (Microsoft disputes); Apple glasses
> timing (rumor); fast-moving LLM model names/prices.
