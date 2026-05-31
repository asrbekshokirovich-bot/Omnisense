# Omnisense — Business Plan (Uzbekistan launch)

> **The product:** a wearable + app that acts as your 24/7 "second brain" — it
> remembers your conversations and meetings (later: what you see) and answers anything
> you ask later, **in Uzbek and Russian.**
> **The business:** sell the hardware **at cost**, make **all** revenue from a **monthly
> subscription**, **first 3 months free.**
> **Launch market:** **Uzbekistan.**

**Status:** v2 — localized for Uzbekistan, grounded in May 2026 research. Companion docs:
[`master-plan.md`](./master-plan.md) (product/tech), [`market-research.md`](./market-research.md)
(global competitive landscape), [`demo-sprint.md`](./demo-sprint.md) (the 30-day demo plan).
Figures are research-backed planning assumptions; sources in §20. *Legal content is
research synthesis, not legal advice — use licensed Uzbek counsel.*

**Context (from you):**
- You run an **existing IT / software company** (team + delivery capacity).
- An **investor** will **test the first product himself**; if he likes it he invests
  **~$1M** (possibly more later).
- Model: hardware **at cost**, **100% subscription revenue**, **first 3 months free**.
- Confirmed: **~$12/mo-equivalent as the business tier**, **annual prepay + card-on-file
  trial**, **launch in Uzbekistan**, **~1-month demo**, **cheap audio pendant** first.

---

## 1. Executive summary

Omnisense is a personal-memory AI for Uzbekistan: a cheap wearable that captures your
conversations and an app that turns them into a private, searchable memory and a daily
briefing — working in **Uzbek and Russian.** Ask it *"what did we agree with the
client?"* and get the answer with the exact quote.

**The model is proven and the market is open.** Hardware + subscription already built
**Oura (~$11B)** and **Whoop (~$10.1B, ~$1.1B revenue)**; **PLAUD** bootstrapped to
~$180–250M ARR selling an AI recorder. Yet **no one has localized this for Uzbekistan** —
a young country of **37M** (median age 27), **~30M smartphone users**, **89% internet
penetration**, and almost no local-language competitor. Meta/Amazon (who just bought
Limitless and Bee) won't build for Uzbek any time soon.

**Our moat is forced by the local constraints — and that's the good news.** Budget
Android phones dominate (so on-device AI is unreliable), **Uzbek is a low-resource
language** that needs a fine-tuned model, and the **data law requires biometric voice
data to stay in Uzbekistan.** The single answer to all three: **self-host a fine-tuned
Uzbek/Russian speech model on servers in Tashkent.** That (a) controls cost at scale,
(b) is privacy-law-compliant by design, and (c) gives us **Uzbek transcription quality
Big Tech won't match** — the defensible edge.

**Economics.** Pricing is localized: a **business/prosumer tier at ~$10–16/seat**
(profitable from day one on cloud transcription) leads, with a **~$2/mo mass tier** that
turns on once self-hosted transcription drops the cost. **IT Park residency** (0% profit/
VAT/social tax, 7.5% payroll) makes our burn tiny, so ~$1M goes very far.

**The plan / ask.** Our existing team builds a working demo in **~1 month** (off-the-
shelf pendant + great software, in Russian/Uzbek). The investor uses it for real; on his
**~$1M**, we fund Uzbek-language R&D, in-country infrastructure, the first hardware batch
(~$80–250k), local payments, and a private beta — proving the **conversion + retention**
that unlock the next round.

---

## 2. The company & why us (unfair advantages)

Not a solo founder — the venture launches from an operating **IT company**:
- **Engineering capacity on day one** (app, backend, AI pipeline) — no hiring from zero.
- **Very low burn** — Uzbek salaries + **IT Park 0% tax** mean ~$1M funds far more than
  it would anywhere else. A real cost moat.
- **Delivery discipline** — a services company ships to deadlines (exactly what a
  1-month demo needs).
- **A committed first investor** — most startups die finding their first check; we start
  with one who will *test the product himself.*

Gap to close: consumer hardware + consumer subscription is a new muscle → mitigate by
**software-first**, off-the-shelf hardware for the demo, hardware/growth hires post-raise.

---

## 3. Problem & solution

**Problem.** People forget decisions, commitments, and details. Notes and recordings
scatter across apps. Existing AI recorders are clunky, weak at "who said what," **don't
speak Uzbek**, and are owned by Big Tech that profits from your data.

**Solution.** Omnisense remembers *for* you and answers in plain Uzbek/Russian. Four use
cases, in order of value and feasibility:

| # | Pillar | Example | Phase |
|---|--------|---------|-------|
| 1 | Conversation & meeting memory | "What did we agree to ship by Friday?" | **Launch** |
| 2 | Screen / digital memory | "What was that link I saw yesterday?" | Early add-on |
| 3 | Find-my-things | "Where did I last see my keys?" | Phase 2 (camera) |
| 4 | Show-me-how | "How did I do this last time?" | Phase 3 (camera) |

Technical detail in [`master-plan.md`](./master-plan.md).

---

## 4. Product strategy

- **Software-first, audio-first.** First product = conversation memory (the proven sticky
  use case; PLAUD's wedge). Cheap to run, least legally fraught, and where competitors are
  weakest (speaker ID). Vision comes after funding.
- **Cheap audio pendant first; glasses later.** Sold at cost, a low-BOM pendant
  (BOM ~$30–45 at low volume) = a low price = adoption. Glasses are a later premium tier.
- **For the demo, no custom hardware** — off-the-shelf/open pendant or phone + clip mic,
  so all effort goes into the software (see [`demo-sprint.md`](./demo-sprint.md)).
- **Bilingual from day one** — Russian works out of the box; **Uzbek is the moat** (§9).

---

## 5. Market opportunity

**Uzbekistan (launch market):**
- **37.1M people, median age 27**, ~half urban; GDP/capita ~$3,180; **~12,100 som = $1**.
- **~30M smartphone users, 89% internet penetration; Telegram reaches ~76%** (25M users);
  Russian used by ~18.5% (urban/Tashkent/business), Uzbek by the majority.
- **TAM** ~28–30M smartphone users · **SAM** ~4–6M urban professionals/students/SMEs ·
  **SOM** ~15,000–50,000 subscribers in 12–24 months (stretch ~100k). At ~$2/mo, 30k subs
  ≈ **~$720k ARR**; the business tier lifts ARPU well above that.
- **Almost no localized competitor** — first-mover advantage in Uzbek.

**The model is proven globally (the comparable that convinces an investor):**

| Company | Model | Scale (2025, est.) | Valuation |
|---|---|---|---|
| **Oura** | Ring + ~$6/mo | 5.5M+ rings, ~$1B rev, ~2M subs | **~$11B** |
| **Whoop** | Subscription-led, hardware bundled | ~$1.1B rev, 2.5M+ members | **~$10.1B** |
| **PLAUD** | AI recorder + subscription | ~$180–250M ARR, 1M+ units | ~$2B |

**Category growth (global):** wearable-AI ~16% CAGR; AI meeting-memory ~20–26% CAGR.

---

## 6. Competition & differentiation

Detail in [`market-research.md`](./market-research.md). **Graveyard:** Humane Pin
(bricked, sold for ~$116M), Rabbit R1, Friend (backlash). **Survivors/threats:** Meta
Ray-Ban (~7M), PLAUD (~1M), Limitless→Meta, Bee→Amazon.

**Our four wedges (Uzbekistan-sharpened):**
1. **Uzbek-language quality** — a fine-tuned, in-country model nobody else offers.
2. **Trust / data residency** — voice data stays in Uzbekistan, encrypted, you hold keys.
3. **Local price & payments** — at-cost device + a ~$2 tier + Payme/Click/BNPL.
4. **Focus** — one beloved use case (conversation memory) done well.

> Big Tech can out-spend us globally but **won't localize for Uzbek** soon. That window
> is the opportunity.

---

## 7. Business model — hardware at cost, revenue from subscription

A razor-and-blades / membership model (validated by Oura & Whoop):
- **Hardware = acquisition, not profit** (priced at manufacturing + expenses).
- **Subscription = the entire business** (high margin once transcription is in-country).
- **First 3 months free** to build the habit — so **free→paid conversion is the #1 metric.**

**Two rules the research makes mandatory:**
1. **Bill annually, upfront (Whoop).** The category churns hard; collecting a year ahead
   front-loads cash and locks users past the risky early months. In Uzbekistan, pair with
   **carrier billing** and **BNPL (Uzum/Click)** for the device.
2. **Be transparent that the device is at-cost and the value is the service.** When Oura
   hid a subscription it got a class-action; our framing makes that an honest story.

---

## 8. Pricing (Uzbekistan)

Localized to local purchasing power, **not** Western numbers. The reference everyone
knows is **Yandex Plus ≈ 16,000 som (~$1.30/mo)**; "normal/cheap" is ~15,000–30,000 som,
**$4+ reads as premium**, and $10–20 is mass-prohibitive. (≈12,100 som = $1.)

| Tier | Price | For whom |
|------|-------|----------|
| **Free** (after trial) | 0 | everyone — recent memory + limited queries; keeps churned users in funnel |
| **Personal** | **~25,000 som/mo (~$2)** | mass consumer — at/just above Yandex Plus; usage-capped |
| **Pro** | **~49,000 som/mo (~$4)** | prosumers — higher caps, priority |
| **Business / seat** | **~120,000–190,000 som (~$10–16)** | Tashkent pros, banking/IT, SMEs — **the profitable beachhead** (≈ the "$12" we set) |

- **Lead with the business/prosumer tier** — price covers cost, and these users have
  capable phones. **Drive down to the ~$2 personal tier once self-hosted transcription
  cuts the cost** (§9).
- **Keep "3 months free"**, paired with a **near-free intro promo** (cf. Yandex's 100-som)
  and **card-on-file / Payme-token auto-convert** to lift conversion.
- **Push annual**; offer **carrier billing + BNPL** to remove price/device friction.

---

## 9. Unit economics & the in-country transcription moat

### The cost problem, and why Uzbekistan needs its own answer
A heavy always-on user produces ~90 hrs/mo of speech. **Cloud transcription costs
~$0.12–0.58/hr → ~$11–52/user/mo** — far above a $2–4 subscription. Elsewhere you fix
this by transcribing **on the phone** (≈$0). **But in Uzbekistan two facts break that:**
budget Android phones can't run it well, and **Uzbek is low-resource** (stock models are
weak; it needs a fine-tuned model).

### The answer: self-hosted, fine-tuned Uzbek/Russian STT in Tashkent (our moat)
This one move solves **cost, law, and quality** simultaneously:
- **Cost:** a fixed GPU cost amortized across many users beats per-minute APIs at scale —
  what makes even a ~$2 tier viable.
- **Law:** voice/biometric data **never leaves Uzbekistan** → compliant with the
  data-localization rule (§16) by design.
- **Quality / moat:** fine-tuned on Uzbek speech data that already exists (**UzbekVoice
  ~1,400 hrs**, Common Voice ~265 hrs), our Uzbek beats Google/Yandex/Big-Tech — something
  incumbents won't bother to do.
- **Phasing:** **demo & early beta → cloud STT** (Yandex SpeechKit supports Uzbek +
  Russian; Google supports `uz-UZ`) to ship fast; **migrate to self-hosted in-country** as
  users grow. **Russian is already well-supported either way.**
- **Recording model:** to control cost *and* consent risk, the consumer tiers are
  **usage-capped / tap-to-record (meetings)** — unlimited 24/7 always-on is a premium
  capability with strong consent UX, not the default.

### Illustrative unit economics
| Metric | Cloud STT, always-on (bad) | **Capped + in-country STT (our plan)** |
|---|---|---|
| Serving cost | ~$11–52/mo | **~$1–4/mo at scale** |
| Business tier ARPU (~$12) margin | thin/negative | **~70–90%** |
| Personal tier ARPU (~$2) | impossible on cloud | **viable once self-hosted** |

**LTV vs churn (the real risk).** AI apps keep only ~21% at 12 months; ~50% of wearables
are abandoned within a year. Mitigate with **annual prepay**, the daily-habit briefing,
and proactive value. Because hardware is at cost (small subsidy), a converted user repays
the free period in ~1–2 paid months — so the levers are **conversion + early retention.**

---

## 10. Funding plan

**Pre-funding (now → demo):** bootstrapped by the existing company — team time, a few
off-the-shelf devices, cloud credits (< ~$30–50k of effort).

**The raise: ~$1M (~18-month runway).** A full pendant program (prototype → first batch)
is only ~$80–250k, so most of the $1M funds **team + Uzbek R&D + runway**, amplified by
IT Park's 0% tax.

| Area | Share *(est.)* | What it buys |
|---|---|---|
| **Product & engineering team** | ~40–50% | App/backend/ML (cheap via your company + IT Park) |
| **Uzbek-language R&D + in-country GPU infra** | ~10–18% | Fine-tuned STT, Tashkent hosting (the moat) |
| **Hardware: design, tooling, certs, first batch** | ~12–18% | Device + EMC/Uzstandard certs, 1k-unit run |
| **Legal, privacy & compliance** | ~5–8% | Data-law registration, consent, counsel |
| **Marketing & community** | ~8–12% | Telegram-led growth, early adopters |
| **Contingency** | ~5–10% | Overruns |

**Deal structure** *(not legal/financial advice)*: a ~$1M pre-seed is commonly a SAFE/
convertible or a small priced round. Leverage: the investor commits **after using a
working product**, which de-risks the check and supports better terms.

---

## 11. The investor demo (how to win the check)

~1 month, existing team, off-the-shelf hardware. The full plan is in
[`demo-sprint.md`](./demo-sprint.md). The goal is the **"I'd be annoyed to lose this"**
feeling: he wears it through real meetings, gets a **morning briefing in his language**,
and asks it questions that it answers with citations. Validate **Russian + Uzbek
transcription in Week 1** (the critical risk). Bring this plan + a simple metrics view to
the close.

**Post-funding milestones:** M1 (0–6mo) product v1 + private beta (100–500) + data-law
foundation; M2 (6–12mo) first hardware batch + public launch + proven conversion/month-4
retention; M3 (12–18mo) scale + next-round metrics.

---

## 12. Go-to-market (Uzbekistan)

- **Beachhead:** Tashkent knowledge workers, banking/IT, SMEs, and students — capable
  phones, higher willingness to pay (business tier).
- **Channel: Telegram first** (76% reach) — channels, bots, communities; plus Instagram
  and YouTube; **influencers** and **telco partnerships** (carrier billing/bundles) over
  expensive paid search.
- **Language:** Uzbek-first UI + Russian; market the **Uzbek-quality** angle proudly.
- **Trust as marketing:** "your voice data stays in Uzbekistan, encrypted — we can't read
  your memories." A credible, local, pro-privacy story.
- **Expansion:** down-market to the ~$2 personal tier as costs fall; later, **Teams/
  Business** (shared memory) and the **vision/glasses** tier; then neighboring CIS/Central
  Asian + Turkic markets (the Uzbek/Russian/Turkic STT investment travels).

---

## 13. Roadmap

| Phase | Timing | Goal | Gate |
|------|--------|------|------|
| **0 · Demo** | ~1 month | Win the investor (software demo on off-the-shelf hardware, RU/UZ) | Investor commits ~$1M |
| **1 · Build v1** | 0–6 mo | Product v1, private beta (100–500), IT Park residency, data-law foundation | Users love it; retention signal |
| **2 · Launch** | 6–12 mo | First hardware batch + certs, public launch, Payme/Click billing, prove conversion | Healthy conversion + month-4 retention |
| **3 · Scale** | 12–18 mo | Self-hosted in-country STT live, ~$2 tier, vision tier, next raise/break-even | Metrics for Series A or profitability |

---

## 14. Team & org

- **Foundation:** your IT company supplies software/backend/ML + delivery.
- **Post-funding hires/contractors:** an **ML/speech engineer** (Uzbek STT fine-tuning),
  a **hardware/embedded** lead, a **consumer growth** owner, and **privacy/legal** counsel.
- **Founder focus:** vision, investor, and business-model discipline (conversion/retention).

---

## 15. Risks & mitigations

| Risk | Why it matters | Mitigation |
|------|----------------|------------|
| **Uzbek transcription quality** | Core value; stock models weak | Fine-tune on UzbekVoice (1,400h); cloud (Yandex) for demo; in-country self-host at scale |
| **Budget phones can't run on-device AI** | Breaks the cheap-margin lever | Self-hosted in-country STT + usage caps |
| **Churn** | AI apps ~21% at 12mo; wearables ~50% abandoned/yr | Annual prepay, daily briefing, retention focus |
| **Weak free→paid conversion** | 3 free months then $0 | Card-on-file/Payme auto-convert, push annual, strong onboarding |
| **Data-law / consent** | Biometric voice must stay in-country; always-listening optics | In-country voice store, register DB, explicit consent, capped/tap-to-record, counsel |
| **Hardware cert/import friction** | EMC + Uzstandard + duties add time/cost | Off-the-shelf for demo; importer-of-record; IT Park customs exemption for dev units |
| **Working capital / inventory** | At-cost units tie up cash | Small first batches (1k), BNPL, no over-ordering (Peloton lesson) |
| **Single-market concentration** | All-in on Uzbekistan | The Uzbek/Russian/Turkic STT moat extends to CIS/Central Asia later |
| **Single-investor dependency** | One "no" stalls everything | Cheap demo → showable to others too |

---

## 16. Privacy, legal & regulatory (Uzbekistan)

*Research synthesis, not legal advice — use licensed Uzbek counsel.*
- **Data localization (changed 2026):** the March 2026 reform **relaxed** blanket
  localization (cross-border allowed with safeguards), **BUT biometric data — voiceprints
  — and telecom data must still be stored in Uzbekistan.** → Architecture: **voice/identity
  store in a Tashkent data center; derived text/memory may go abroad** (watch the pending
  "adequate-country" list; keep a localized fallback). **Register the database** with the
  State Personalization Center — non-compliance triggers fines (~$1,400 → criminal
  ~$4,300) and **app blocking** via the "Register of Infringers."
- **Consent:** explicit consent is the lawful basis. Design consent for the **user** *and*
  a defensible position on **bystander voice capture** (the always-listening risk) — the
  household/personal-use exemption likely won't cover a commercial cloud service.
- **Universal must-haves (also our brand):** default-OFF, encrypted, one-tap delete, clear
  recording indicator, **no emotion/biometric profiling**, capped/tap-to-record default.

---

## 17. Operating playbook (Uzbekistan specifics)

- **IT Park residency (do this early):** 0% profit/turnover/VAT/social tax, **7.5%**
  payroll income tax, **VAT on imported services waived** (helps buying foreign cloud/AI),
  through 2028 (2040 if >50% export revenue). Grants: up to **$20k** incubation, **$100k**
  IT Park Ventures co-invest, **$1M** President Tech Award. *Confirm your subscription SaaS
  isn't reclassified into the excluded payment/marketplace bucket (rule changed Apr 2026).*
- **Payments:** integrate **Payme + Click recurring APIs** (PayTechUZ wraps Payme/Click/
  Atmos); add **carrier billing** and **BNPL (Uzum/Click)** for the device. Uzcard/Humo are
  the card rails.
- **Hardware import/sale:** budget for **EMC type approval (Ministry of Digital Tech) +
  Uzstandard certification per SKU**, a **local importer-of-record**, **E-Contract**
  registration, ~**12% import VAT + ~10–20% consumer-electronics duty** (IT Park customs
  exemption helps for *dev* units, not resale stock).
- **Compute:** demo/beta on cloud (Yandex SpeechKit / Google `uz-UZ`); **self-hosted
  fine-tuned Whisper-medium on Tashkent GPUs** at scale (cost + law + Uzbek-quality moat).

---

## 18. Assumptions — confirmed & remaining

**Confirmed with you:** business tier ≈ $12/mo · annual prepay + card-on-file trial ·
**Uzbekistan** launch · **~1-month** demo · **audio pendant** entry device.

**Still to decide (we can take these as we go):**
1. Lead segment — agree we **start with the business/prosumer tier** (Tashkent pros/SMEs)
   and add the ~$2 personal tier after self-hosted STT? *(recommended)*
2. Demo language — **Russian first**, Uzbek as the funded moat, or push Uzbek into the
   demo immediately?
3. Pendant for the demo — buy **Omi (open)**, or simplest **phone + clip-on mic**?

---

## 19. Key metrics

Activation (first memory), D1/D7/D30 retention, **free→paid conversion**, **month-4
retention**, **transcription accuracy (Uzbek & Russian)**, cost/active user, ARPU, gross
margin, churn, annual-plan mix, referral rate.

---

## 20. Sources (key figures)

**Global market/benchmarks/comparables:** Research and Markets, MarketsandMarkets, Grand
View (wearables/glasses); MarketIntelo/Technavio/MRFR (AI note-takers); RevenueCat &
ChartMogul (AI-app churn); CNBC/BusinessWire/Sacra (Oura), Yahoo Finance/Sacra (Whoop),
Sacra/ARR Club (PLAUD). **Costs:** Fanstel & Omi/Based Hardware (BOM), Zetarmold (tooling),
Bluetooth SIG/JJRLAB (certs), Deepgram/Soniox/AssemblyAI (STT). **Uzbekistan market:**
Worldometer/DataReportal/IMF (demographics, internet, Telegram), UzDaily/Kun.uz/wage.is
(salaries), UzDaily/Ucell (Yandex Plus pricing), Esplora Legal/KPMG & Payme/Click/PayTechUZ
docs (payments). **Uzbekistan legal/IT Park/ASR:** Dentons/settleadvisory/dataguidance &
loc.gov (data-localization 2026 reform + biometric carve-out), dlapiper (privacy), Mondaq/
EY/it-park.uz (IT Park incentives), trade.gov/PwC/ib-lenhardt/TÜV SÜD (import/EMC certs),
HuggingFace/MDPI/Nature/Yandex/Google Cloud docs & UzbekVoice.ai (Uzbek + Russian STT).
Full URLs are preserved in the research transcripts and [`market-research.md`](./market-research.md).

*Companion docs: [`master-plan.md`](./master-plan.md), [`market-research.md`](./market-research.md),
[`demo-sprint.md`](./demo-sprint.md). Visual brief: [`omnisense-report.html`](./omnisense-report.html).*
