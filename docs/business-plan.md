# Omnisense — Business Plan

> **The product:** a wearable + app that acts as your 24/7 "second brain" — it
> remembers your conversations, meetings, and (later) what you see, and answers
> anything you ask later.
> **The business:** sell the hardware **at cost**, make **all** revenue from a
> **monthly subscription**, and give every new user the **first 3 months free.**

**Status:** v1 business plan, grounded in May 2026 research. Companion docs:
[`master-plan.md`](./master-plan.md) (product & technical plan) and
[`market-research.md`](./market-research.md) (sourced competitive landscape). Figures
are research-backed *planning assumptions*, not commitments; sources are listed in §19.

**Context this plan is built on (from you):**
- You are **not a solo founder** — you run an **existing IT / software outsourcing
  company**, so you have an engineering team and delivery capacity.
- You have an **investor** who will **test the first working product himself**; if he
  likes it, he invests **~$1M (possibly more over time).**
- **Business model:** hardware sold **at cost** (manufacturing + direct expenses, **no
  hardware profit**); **100% of income from subscriptions**; **first ~3 months free.**

---

## 1. Executive summary

Omnisense is a personal-memory AI: a small wearable that captures your conversations
(and later what you see), plus an app that turns them into a private, searchable memory
and a proactive daily briefing. Ask it *"what did I promise the client?"*, *"where did I
leave my keys?"*, or *"how did I fix this last time?"*

**The market is validated and the model is proven.** The AI-note/meeting-memory
category we're entering is growing **~20–26%/year**; broader wearable-AI is a **~$54B
market growing ~16%/year** to ~$112B by 2030. More importantly, our exact business model
— **hardware + subscription** — already built **Oura (~$11B valuation)** and **Whoop
(~$10.1B, ~$1.1B revenue, cash-flow positive)**, and **PLAUD bootstrapped to ~$180–250M
ARR** selling an AI voice recorder. In 2025, **Meta acquired Limitless and Amazon
acquired Bee** — validating demand *and* signaling the threat: incumbents will
commoditize basic audio memory.

**Our wedge is the one thing Big Tech structurally can't offer: trust** — a
privacy-first, **on-device, "your memories stay yours"** product. This isn't just
positioning; it's also our margin engine. By transcribing audio **on the phone** instead
of the cloud, we cut serving cost from **~$12–20/user/mo to ~$0.50–4** — the difference
between negative and **70–95% gross margins.** The same choice protects privacy *and*
makes a low subscription price profitable.

**The business model:** sell hardware **at cost** to remove the adoption barrier and
reach scale, then earn durable, high-margin **subscription** revenue. The first 3 months
are free to build the daily habit before we charge. We'll **bill annually upfront**
(the Whoop playbook) to beat the category's brutal churn.

**The plan / the ask:** Using our existing software company, we build a polished,
genuinely useful **demo** for the investor in ~8–12 weeks (lean — off-the-shelf hardware
+ great software, no custom tooling yet). On his commitment of **~$1M**, we fund a
~18-month plan to ship real hardware (a first batch costs only ~$80–250k), launch
publicly, and prove the **retention + free-to-paid conversion** that unlock a larger
round or profitability.

**Why we can win:** an existing engineering team (far lower burn than a typical
startup), a committed first investor, a trust-led position against Big Tech, and an
edge-first architecture that is simultaneously our privacy story and our margin story.

---

## 2. The company & why us (unfair advantages)

This is **not** a solo founder learning to code. The venture launches from an operating
**IT / outsourcing company**:

- **Engineering capacity on day one** — build the app, backend, and AI pipeline with our
  own team instead of hiring from zero.
- **Lower burn / longer runway** — outsourcing-company economics mean ~$1M funds far
  more engineer-months than for a Bay-Area startup. A real cost moat.
- **Delivery discipline** — a services company already ships to deadlines, exactly what
  an investor demo needs.
- **A committed first investor** — most startups die looking for their first check; we
  start with one who will *test the product himself.*

**The one gap to close:** consumer hardware + a consumer subscription is a different
muscle than B2B services. We mitigate by **starting software-first**, using **off-the-
shelf/open hardware** for the demo, and hiring hardware/consumer-growth expertise only
**after** funding.

---

## 3. Problem & solution

**Problem.** People forget almost everything — decisions, commitments, where they put
things, how they did something. We scatter notes, screenshots, and recordings across a
dozen apps and still can't find anything. Existing AI recorders help a little but are
clunky, weak at "who said what," and increasingly owned by Big Tech that profits from
your data.

**Solution.** Omnisense remembers *for* you, automatically, and lets you ask in plain
language. Four use cases, shipped in order of value and feasibility:

| # | Pillar | Example | Phase |
|---|--------|---------|-------|
| 1 | Conversation & meeting memory | "What did we agree to ship by Friday?" | **Launch** |
| 2 | Screen / digital memory | "What was that link I saw yesterday?" | Early add-on |
| 3 | Find-my-things | "Where did I last see my keys?" | Phase 2 (camera) |
| 4 | Show-me-how | "How did I do this last time?" | Phase 3 (camera) |

Technical detail lives in [`master-plan.md`](./master-plan.md). This plan's job is to
show why this is a fundable, profitable company.

---

## 4. Product strategy (what we ship, and when)

- **Software-first, audio-first.** The first product is conversation memory — the proven
  sticky use case (it made PLAUD #1). It's cheap to run, the least legally fraught, and
  the place every competitor is weak (speaker identification = our quality edge). Vision
  comes after funding.
- **The entry device is deliberately cheap and simple** — a pendant/clip-class audio
  wearable. Because we sell at cost, a **low-BOM device = a low price = mass adoption**,
  which is the whole point of the model. Premium **glasses** (camera, the full vision
  experience) come as a **later, higher tier**, not the entry product.
- **For the investor demo, do NOT build custom hardware.** Use an **off-the-shelf or
  open-source device** (the open Omi pendant, or a clean phone-+-mic setup) so 100% of
  pre-funding effort goes into making the **software undeniable.** Tooling and
  certification are funded *after* the investor commits.

---

## 5. Market opportunity

**The category is validated and growing fast** (sources in §19):

- **Wearable AI:** ~**$53.7B (2025) → ~$112.3B (2030), ~16% CAGR** (Research and
  Markets); analysts cluster at ~16–18%.
- **Smart glasses (the hot adjacency):** ~$1.22B (2025) → ~$4.13B (2030), **~29% CAGR**;
  shipments grew **+110% YoY in H1 2025** with Meta holding >70% share (Counterpoint).
- **AI note-takers / meeting memory (our actual category):** ~$2.8B (2025) → ~$14.6B
  (2034), **~20% CAGR**; the meeting-assistant sub-segment compounds even faster at
  **~25.6% CAGR.** This is growing faster than wearables broadly.

**The model itself is proven — it built ~$10B companies:**

| Company | Model | Scale (2025, est.) | Valuation |
|---|---|---|---|
| **Oura** | Ring + ~$6/mo sub | 5.5M+ rings, ~$1B rev, ~2M paying subs | **~$11B** |
| **Whoop** | Hardware-bundled, subscription-led | ~$1.1B rev (+103% YoY), 2.5M+ members, cash-flow positive | **~$10.1B** |
| **PLAUD** | AI recorder + subscription | ~$180–250M ARR, 1M+ units | ~$2B *(single-source)* |
| **Otter.ai** | AI meeting notes (SaaS) | ~$100M ARR, 35M+ users | — |

**Our beachhead (SOM).** Don't boil the ocean. Start with the audience PLAUD proved will
pay: **meeting-heavy knowledge workers** — founders, consultants, sales, students,
journalists. Land there, then expand to the broader "remember my life" consumer market
with the cheaper device and the vision features.

---

## 6. Competitive landscape & differentiation

Full detail in [`market-research.md`](./market-research.md). Short version:

**The graveyard:** Humane AI Pin (tried to replace the phone; bricked; assets sold for
~$116M), Rabbit R1 ("$199 toy that fails at almost everything"), Friend (always-on
"companion"; public backlash).

**The survivors / threats:** Meta Ray-Ban (~7M units), PLAUD (~1M, audio leader),
**Limitless→Meta**, **Bee→Amazon**.

**Our differentiation (four wedges):**
1. **Trust / privacy-first.** Local-first, on-device processing, encrypted, *you hold
   the keys.* The credible thing a small independent can say that Meta/Amazon cannot.
2. **"Who said what" done right.** Best-in-class speaker identification — the universal
   weak point of every competitor.
3. **Price / access.** Hardware at cost → the lowest barrier to entry in the category.
4. **Focus.** One beloved use case done better than a does-everything incumbent.

> **Honest risk:** Amazon and Meta can *also* subsidize hardware and have huge
> distribution. We do **not** win on price alone — price gets us in the door; **trust +
> product quality + retention** is what keeps us alive.

---

## 7. Business model — hardware at cost, revenue from subscription

A **razor-and-blades / "membership"** model, validated by Oura and Whoop:

- **Hardware = customer acquisition, not profit.** We price the device at
  **manufacturing + direct expenses** (≈ break-even; pendant BOM is only ~$30–45 at low
  volume, falling to ~$18–28 at scale). The device exists to get the app onto someone's
  body and start the memory habit.
- **Subscription = the entire business.** All margin comes from a recurring fee for the
  AI memory service.
- **First ~3 months free**, then convert to paid. This lifts activation but **delays
  revenue and adds serving cost during the free window**, so **free-to-paid conversion
  is the single most important metric.**

**Two design choices the research makes mandatory:**

1. **Bill annually, upfront (the Whoop playbook).** The category's churn is brutal (see
   §9). Whoop blunts it by collecting a year in advance, which front-loads cash and locks
   users past the high-churn early months. We should **push an annual prepay** (with a
   monthly option) — ideally the **at-cost device is tied to an annual commitment.**
2. **Be radically transparent that the device is at-cost and the value is the
   subscription.** When **Oura** quietly added a subscription and gated features, buyers
   felt "bait-and-switched" → a **2026 class-action lawsuit.** Our at-cost framing turns
   that liability into an honest, sympathetic story: *"we don't profit from the device —
   only from making it useful."*

**Why this fits us:** maximizes adoption (a memory product is a daily habit of one),
recurring revenue is what investors value, and trust + edge-first processing defends the
margin. **Why it's dangerous:** if people churn after the free period, we've given a
device at cost *and* served them free for 3 months. The whole plan must obsess over
**retention.**

---

## 8. Pricing

*(Recommended; competitors sit at $8–20/mo, with always-on wearables anchored at $19 —
Limitless and Bee both $19/mo. PLAUD Pro is $17.99/mo or $99.99/yr.)*

| Tier | Price *(recommended)* | What's included |
|------|------|------------------|
| **Free (after trial)** | $0 | Thin "safety net" — recent memory only, limited queries. Keeps churned users in the funnel, not gone forever. |
| **Pro** | **~$11.99/mo**, or **~$99/yr (~$8.25/mo)** | Unlimited memory, full search, daily briefing, speaker ID, integrations. The core offer. |
| **(Later) Premium / Vision** | higher | Glasses tier, find-my-things, show-me-how, family features. |
| **(Later) Teams/Business** | per-seat | Shared team memory, admin, compliance — higher ARPU, stickier. |

- **Deliberately undercut the $19 incumbents.** Because on-device processing keeps our
  cost at ~$0.50–4/user/mo, even **~$10–12/mo is a 70–90% margin** — so we can use price
  as an adoption weapon (your "sell cheap" philosophy) and still be profitable. $19 is the
  ceiling the market tolerates; we don't need it.
- **Push annual hard** (~$99/yr) — better cash flow, far better retention.
- **3-month free trial with a card on file ("opt-out")** — research shows opt-out trials
  convert ~**49%** vs ~18% for opt-in. This single choice roughly **doubles conversion**
  while still honoring "first 3 months free."
- **Keep a free tier** rather than a hard wall, so a price-sensitive user stays a user
  (and a future upsell) instead of churning to zero.

---

## 9. Unit economics & financial model

### The make-or-break insight: edge-first processing (validated)
A naïve cloud design **loses money.** At ~3 hrs/day of actual speech (after silence
filtering) ≈ **90 hrs/user/mo**, cloud transcription + speaker ID costs:

| Approach | Cost / user / mo |
|---|---|
| Cloud STT — Deepgram (~$0.58/hr) | ~$52 ❌ |
| Cloud STT — Soniox (~$0.12/hr, diarization bundled) | ~$10.80 |
| + embeddings + LLM digests/queries + storage | **~$12–20 total ❌ (≈ the whole subscription)** |
| **On-device transcription (faster-whisper on phone) + cloud only for embeddings/LLM** | **~$0.50–4 ✅** |

On-device transcription drops the dominant cost line to ~$0 (Whisper Large-V3-Turbo runs
~10× real-time on a modern phone). **This one architectural choice — on-device by default
— is simultaneously our privacy differentiator AND what makes the subscription
profitable.** A hybrid (on-device default, cloud for hard audio) is the pragmatic path.

### Illustrative unit economics *(per Pro user)*
| Metric | Cloud-only (bad) | **Edge-first (our plan)** |
|---|---|---|
| ARPU | ~$11–12/mo | ~$11–12/mo |
| Serving cost | ~$12–20/mo | **~$2–4/mo** |
| Gross margin | **negative** | **~70–85%** |
| Gross profit / user | — | **~$8–10/mo** |
| Hardware margin | ~$0 (sold at cost) | ~$0 (sold at cost) |

### LTV / CAC and the payback math
**The good news:** because we sell hardware **at cost** (not free, like Whoop), our
per-user cash subsidy is small — essentially just the **~3 free months of serving
(~$1.50–12)** plus marketing CAC. At ~$8–10/mo gross profit, a converted user **repays
the free period in ~1–2 paid months.**

**The risk:** the category churns hard. Stress-test with realistic numbers:

| Scenario | Monthly churn | Avg paid lifetime | LTV (gross profit) |
|---|---|---|---|
| Optimistic | ~5% | ~20 mo | ~$180 |
| **Base (AI-app realistic)** | ~7% | ~14 mo | **~$125** |
| Pessimistic | ~9% | ~11 mo | ~$95 |

> Benchmarks behind this: AI apps retain only **~21% at 12 months** (vs 31% non-AI);
> ~50% of wearables are **abandoned within a year**; only ~10% of monthly subscribers
> reach year two. **Assume the high end of churn and design against it** (annual prepay,
> daily-habit features, the morning briefing). Keep all-in **CAC < ~$35–45** (favor
> organic/referral) to hold **LTV/CAC > 3×.**

### Rough company economics
At ~$9 gross profit/user/mo, **~4,000–5,000 paying users ≈ ~$40–45k/mo gross profit** —
enough to cover a lean team's serving + meaningful opex. With the outsourcing company's
lower labor cost, the path to sustainability is far shorter than for a typical venture.
*(Detailed P&L scenarios can be built once price and team size are fixed.)*

---

## 10. Funding plan

### Pre-funding (now → investor demo)
Funded by the existing company (bootstrap) — keep it cheap. Mostly **team time**, a few
off-the-shelf devices, and cloud credits *(< ~$30–50k of effort).* Deliverable: a
**working, genuinely useful demo** the investor can live with for a week and not want to
give back.

### The raise: ~$1M (target ~18-month runway)
*(Illustrative — tune to the final number and your cost base. Note: a full pendant
program from prototype to first batch is only ~$80–250k, so most of the $1M funds team +
runway, not hardware.)*

| Area | Share *(est.)* | What it buys |
|---|---|---|
| **Product & engineering team** | ~45–55% | App/backend/ML team (cheaper via your company) |
| **Hardware: design, tooling, first batch, certs** | ~12–20% | Custom device, FCC/CE/Bluetooth certs (~$6–15k), first 1,000-unit run |
| **Cloud & AI infrastructure** | ~5–10% | Serving, model usage, storage during growth |
| **Legal, privacy & compliance** | ~5–8% | Recording-law/GDPR/biometric counsel — non-optional |
| **Marketing & community / first users** | ~8–15% | Content, referrals, early-adopter program |
| **Contingency** | ~5–10% | Overruns (hardware always overruns) |

### Deal structure *(not legal/financial advice — use an advisor)*
A ~$1M pre-seed is commonly a **SAFE/convertible** or a priced round around a
single-digit-million post-money valuation. Your leverage: you arrive with **a working
product the investor has personally validated**, which de-risks the check and supports
better terms. Tie the next raise to clear milestones (below).

---

## 11. The investor demo plan (how to win the check)

The investor decides by *using* the product, so the demo must produce the **"I'd be
annoyed to lose this"** feeling. Plan (~8–12 weeks, your existing team):

1. **Pick demo hardware** — off-the-shelf/open pendant or a clean phone+mic. No custom
   hardware yet.
2. **Build the core loop, polished:** capture → on-device transcription → speaker ID →
   memory → ask-anything → **morning briefing** (the "wow").
3. **Make recall feel magical and fast** — sub-second, accurate, with citations ("at
   2:14pm you told Sara…").
4. **Make the trust story tangible** — on-device processing, encryption, one-tap delete,
   default-off. He should *feel* the privacy difference.
5. **Have him use it for a real week** on his own meetings; instrument it so you can show
   him *his* usage and the value it produced.
6. **Bring this plan + a simple metrics dashboard** to the close.

**Milestones to put in front of the investor (post-funding):**
- **M1 (0–6 mo):** real product v1, custom hardware design started, **private beta
  (100–500 users)**, privacy/legal foundation in place.
- **M2 (6–12 mo):** **first manufacturing batch**, public launch, **prove free→paid
  conversion and month-3 retention**, 1k–10k users.
- **M3 (12–18 mo):** scale + metrics that unlock a larger round or break-even.

---

## 12. Go-to-market

- **Beachhead:** meeting-heavy knowledge workers (the PLAUD audience).
- **Motion:** **product-led + community.** Free 3 months + at-cost device = the lowest-
  friction trial in the category. Lean on **referrals** (memory is demo-able to friends),
  **content/SEO** ("AI meeting memory"), and **founder/creator word-of-mouth.** Avoid
  burning cash on paid ads until retention is proven.
- **Trust as marketing:** publish the privacy architecture openly; make "we can't read
  your memories" a headline, not fine print — directly contrasting the Big Tech owners.
- **Expansion:** consumer "remember everything" mass market (cheap device + vision),
  then **Teams/Business** (shared memory, higher ARPU, stickier).

---

## 13. Roadmap

| Phase | Timing | Goal | Gate to advance |
|------|--------|------|-----------------|
| **0 · Demo** | Now → ~12 wks | Win the investor with a polished software demo on off-the-shelf hardware | Investor commits ~$1M |
| **1 · Build v1** | 0–6 mo post-raise | Real product, private beta (100–500), privacy/legal foundation | Users love it; retention signal |
| **2 · Launch** | 6–12 mo | First hardware batch, public launch, prove free→paid conversion | Healthy conversion + month-3 retention |
| **3 · Scale** | 12–18 mo | Grow users, add vision tier, prep next raise / break-even | Metrics for Series A or profitability |

---

## 14. Team & org

- **Foundation:** your IT/outsourcing company supplies **software, backend, and ML
  engineering** + delivery management.
- **Key early hires/contractors (post-funding):** a **hardware/embedded** lead (the main
  capability gap), a **consumer product/growth** owner, and **privacy/legal** counsel
  (fractional is fine).
- **Founder focus:** vision, the investor relationship, and — critically — business-model
  discipline (retention, conversion, unit economics).

---

## 15. Risks & mitigations

| Risk | Why it matters | Mitigation |
|------|----------------|------------|
| **Churn (the #1 risk)** | AI apps keep only ~21% at 12 mo; ~50% of wearables abandoned within a year | **Annual prepay (Whoop)**, daily-habit features (briefing), proactive value, retention > acquisition |
| **Weak free→paid conversion** | 3 free months then $0 if they don't convert | **Card-on-file opt-out trial (~49% vs ~18%)**, strong onboarding, push annual |
| **Cloud cost > subscription** | Kills margins | **Edge-first / on-device transcription** (also the privacy win) |
| **Working capital / inventory** | We pay for at-cost units up front; over-ordering sank Peloton | **Small first batches (1k)**, off-the-shelf for demo, 3D-printed enclosures first, contingency budget |
| **Selling at cost = no buffer** | Returns/warranty/support have no hardware margin | Price subscription to cover support; keep device simple/reliable |
| **Big Tech (Meta/Amazon)** | Can subsidize + distribute; may absorb the category | Compete on **trust + focus + quality**, not price; move fast on the niche |
| **"Bait-and-switch" perception** | Oura got a class-action for gating features behind a new sub | **Radical transparency**: device at cost, value is the service — said loudly upfront |
| **Privacy/legal exposure** | Recording laws, GDPR, biometrics | Default-off, on-device, consent UX, regional gating, counsel (§16) |
| **Single-investor dependency** | One "no" stalls everything | Build demo cheaply so you can show others too; don't over-fit to one person |

---

## 16. Privacy, legal & regulatory (condensed — it's existential)

An always-on recorder is legally and socially radioactive if done wrong (see Microsoft
Recall's meltdown in [`market-research.md`](./market-research.md)). Non-negotiables —
**and they double as our brand**:
- **Default OFF**, **on-device by default**, **encrypted everywhere**, **one-tap delete.**
- **Clear recording indicator** + **bystander consent** (capture owner's voice by default).
- **No emotion/biometric-categorization features** (banned in the EU AI Act).
- **Recording-consent law** varies (~11–12 US "all-party" states; GDPR; Illinois BIPA for
  voiceprints) → **regional feature-gating** + **legal counsel before public launch.**
- *This section is research synthesis, not legal advice.*

---

## 17. Key metrics to track from day one

Activation (first memory captured), **D1/D7/D30 retention**, **free→paid conversion**,
**month-4 retention** (post free-trial cliff), **cloud cost per active user**, ARPU,
gross margin, **churn**, LTV/CAC, annual-plan mix, and referral rate. The model lives or
dies on the **conversion + retention** pair.

---

## 18. Assumptions to confirm with you

So I can finalize the numbers, please confirm or correct:
1. **Subscription price** — is ~$11.99/mo (annual ~$99) the right band, or
   cheaper/higher? (Market ceiling is ~$19.)
2. **Annual prepay + card-on-file trial** — OK to use these to fight churn while keeping
   "3 months free"?
3. **Target market / geography** for launch (affects pricing, legal, TAM).
4. **Timeline** to the investor demo — is ~8–12 weeks realistic for your team?
5. **Entry device** — start with a cheap **audio pendant** (glasses as a later premium
   tier), or do you want glasses in the first product?

---

## 19. Sources (key figures)

Market & benchmarks: Research and Markets (wearable AI), MarketsandMarkets & Grand View
(smart glasses), MarketIntelo/Technavio & Market Research Future (AI note-takers),
Counterpoint (smart-glasses shipments), RevenueCat *State of Subscription Apps 2025* &
ChartMogul (AI-app churn), First Page Sage/Userpilot (trial/freemium conversion),
ScienceDirect/Centercode (wearable abandonment). Comparables: CNBC/BusinessWire/Sacra
(Oura), Yahoo Finance/Sacra (Whoop), Sacra/ARR Club/36Kr (PLAUD), Otter.ai (ARR).
Costs: Fanstel & Omi/Based Hardware (BOM), Zetarmold (tooling), JJRLAB & Bluetooth SIG
(certs), Deepgram/Soniox/AssemblyAI (STT pricing), OpenAI/IntuitionLabs (embeddings/LLM).
Full URLs are preserved in the research transcripts and [`market-research.md`](./market-research.md).

*Companion documents: [`master-plan.md`](./master-plan.md) (product & technical plan),
[`market-research.md`](./market-research.md) (competitive landscape). A visual,
investor-friendly HTML version of this plan is at [`omnisense-report.html`](./omnisense-report.html).*
