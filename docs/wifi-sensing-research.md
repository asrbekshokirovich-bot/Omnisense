# Wi-Fi Sensing — Research Report for Omnisense

> **Status:** research / strategy. No code change in this commit. Tracked-adjacent.

## Executive Summary

A 2025 study at KASTEL (Karlsruhe Institute of Technology) demonstrated near-100% identification of 197 individuals using only the unencrypted feedback packets (**BFI — Beam Forming Feedback Information**) routinely emitted by every modern Wi-Fi router. The subjects didn't carry phones, didn't touch any screens, and weren't on the network. A few seconds of standing in the room was enough.

This builds on a 13-year research arc:

- **2012** — Karl Woodbridge & Kevin Chetty (UCL London): Wi-Fi could detect movement through walls.
- **2018** — MIT CSAIL's RF-Pose: skeleton-pose estimation from radio reflections.
- **2022** — "DensePose from WiFi" (CMU): full 3D body surface estimation from 3 antennas.
- **2025** — KIT/KASTEL: passive biometric identification at scale, no cooperation required.
- **2025** — IEEE finalized the **802.11bf** standard, formalizing Wi-Fi as a sensing platform.

The technology operates on a physics principle that nothing in software can patch: the human body (~60 % water) bends, reflects, and absorbs 2.4 / 5 / 6 GHz signals in ways that produce a unique "RF gait signature." A radio-frequency shadow of the body, persistent in the air around it.

For Omnisense, this raises four distinct questions:

1. **Feature opportunity** — can we use Wi-Fi sensing as a passive context layer to enrich meeting memory?
2. **Privacy threat** — does Wi-Fi sensing undermine Omnisense's privacy positioning?
3. **Defensive feature** — should Omnisense detect Wi-Fi sensing attempts targeting its users?
4. **Adjacent market** — does this open a follow-on product (smart-home, eldercare, public-safety)?

## The technology in plain terms

### What is actually being measured

Every modern router (Wi-Fi 5 / 802.11ac onward) emits **BFI packets** dozens of times per second. The protocol designers in 2013 chose to send BFI in plaintext to keep latency low — a deliberate performance trade-off, not an oversight. BFI carries **CSI** (Channel State Information) — a complex-valued matrix describing how the radio channel between every antenna pair is behaving in real time.

When a human body is in the channel, BFI changes. The Fourier-domain shape of those changes encodes:

- **Gross movement** (1–2 Hz components: walking, sitting, standing)
- **Micro-motion** (10–30 Hz: chest rise/fall — breathing, heart rate)
- **Body morphology** (the time-invariant DC offsets specific to height, mass distribution, posture)

### What's new

CSI has been observable for ten years. What changed in 2024–25 is that contrastive-learning models — the same family driving face recognition — can pull a person-specific embedding out of a few seconds of CSI. The KASTEL paper reports 99.8 % identification accuracy on 197 enrolled subjects with 3–5 seconds of observation.

This is enrollment-based: the system doesn't recognize strangers, it matches against a stored template, exactly like fingerprint ID. The "scary" framing in popular press conflates "can identify enrolled subjects" with "can identify anyone." They are not the same. Yet.

### What's not happening yet

- **802.11bf isn't deployed.** The standard was finalized in 2025; commodity routers won't ship with bf firmware until 2027+. Today's Wi-Fi sensing requires either custom firmware (Atheros CSI Tool, Nexmon CSI on Broadcom chipsets, esp-csi for ESP32-S3) or specialized SDRs (HackRF, Pluto SDR, USRP).
- **Real-world performance is not the lab number.** 197 cooperating subjects in a quiet room is not 50,000 people in an airport with 12–200 active devices, structural multipath, and adversarial blockers.

## Specific applications for Omnisense

### Tier A — plausible product features (12–18 month horizon)

**A1. Auto-trigger capture from passive presence**

- *What:* When the user's home/office router (or a paired ESP32 with CSI access) detects the wearer entering a known room, Omnisense suggests "start recording the X meeting?" without requiring a button press.
- *Why it matters:* The hardest UX problem in lifelogging is friction-to-start. If 80 % of meetings begin with "should I have hit record?", a passive presence sensor solves it.
- *Privacy:* The trigger is local. CSI never leaves the wearer's router. It emits a webhook to the wearable.
- *Build cost:* Medium. Need either firmware-flashable router (ASUS RT-AX86U + custom plugin) or a separate ESP32-S3 sensor (~$10 BOM). Not Phase-0; Phase-3 R&D.

**A2. Speaker-presence ground truth for diarization**

- *What:* We already have pyannote-based diarization (shipped on this branch). If we also know "Aziz was physically present in the room from 14:02 to 14:47" via his RF signature, we can disambiguate when audio is muddy (overlapping speakers, far-field mics, off-axis voices).
- *Why it matters:* Diarization quality is the #2 driver (after STT accuracy) of perceived memory quality. Hybrid audio + RF improves both.
- *Privacy:* RF signatures of identified individuals are stored as one-way embeddings (same approach as voiceprints already in `app/diarization.py`). Requires explicit owner enrollment + per-individual consent in the consent log.

**A3. "Who else is here" enrichment**

- *What:* During a meeting recording, the wearable notes "3 unknown signatures present" or "Aziz + 2 unenrolled signatures." Later queries can ask about that.
- *Why it matters:* Memory is more useful with social context. "Who was in the room when Aziz said the contract was due?" becomes answerable.
- *Privacy:* This is mass-surveillance-flavored if done badly. Unenrolled signatures must be stored only as anonymous opaque tokens, never tied back to identities the wearer didn't explicitly enroll. Subject to one-tap delete cascading from `/data`.

### Tier B — adjacent products (24–36 month horizon)

**B1. Eldercare bolt-on on the same hardware/cloud**

Wi-Fi sensing + Omnisense memory could detect: fall, breathing-rate anomaly, prolonged inactivity, sleep-disturbance pattern. Uzbekistan demographics — aging population in cities, families increasingly geographically split, low penetration of dedicated eldercare tech. Pricing: 50,000–150,000 som/month, B2B2C via hospitals and insurance partners. Goes to market alongside the consumer SKU, same Tashkent stack.

**B2. Office-room intelligence**

Anonymous occupancy + meeting-active detection for SMB customers. Counts heads, attention time, meeting-effectiveness scoring combined with what Omnisense already does from audio.

### Tier C — defensive feature

**C1. RF-surveillance detection — the "your voice data stays in Uzbekistan" companion**

- *What:* A companion sensor (or built into the app, when phone radios expose enough) that detects whether the room you're in is being passively sensed by an unfamiliar Wi-Fi router — i.e. someone is trying to identify you via your RF signature.
- *Why it matters:* Omnisense's positioning is "your voice data stays in Uzbekistan." Add: "and we'll tell you when someone is trying to passively identify you in public spaces."
- This is the kind of feature that gets press, gets the founder on Telegram, and validates the privacy-moat narrative.

## Threat model implications

If Wi-Fi sensing becomes common — which it will, with 802.11bf — the following Omnisense privacy claims need updates:

1. **"Default-OFF capture."** True for audio. But the wearable's body itself is a beacon. We don't capture; the environment captures *us*. The honest framing: *"Omnisense doesn't capture audio without your consent. But your physical presence is detectable by other systems regardless of what Omnisense does."*
2. **"Your data stays in Uzbekistan."** Voice — yes. But your RF identity may already exist in foreign cloud datasets (e.g. from hotel routers with sensing firmware). Acknowledge in `docs/data-residency.md`.
3. **Threat actors:** foreign intel, competitor commercial intelligence, jealous partners — all become RF-relevant. The Pro and Business tiers serve customers for whom this matters.

## Technical feasibility

| Capability | What it needs | Today (2026) | 2028+ |
|---|---|---|---|
| BFI / CSI extraction | Compatible router firmware | ASUS RT-AX86U + Asuswrt-Merlin custom plugin, or ESP32-S3 + esp-csi (~$10 BOM) | Stock 802.11bf router |
| Identification model | Labeled CSI dataset | KASTEL released architecture (not weights). Fine-tune on Uzbek room/router conditions | Commodity SDK |
| Pose / breathing | RF-Pose / DensePose-from-WiFi architectures | MIT and CMU code on GitHub; GPU needed for training | Edge-deployable |
| Outdoor / public-space sensing | — | Not feasible — multipath chaos | Possible with 6 GHz / mmWave Wi-Fi 7 |

Realistic path for Omnisense:

1. **Phase 0–1 (now → Q4 2026):** Do not build. Cite in research. Add the threat-model paragraph to `docs/data-residency.md`. Add the tracked-adjacent paragraph to `docs/development-plan.md`.
2. **Phase 2 (2027):** Pilot. Order 5–10× ESP32-S3-DevKitC + esp-csi ($75 total via AliExpress to Tashkent). Prototype A2 (speaker-presence ground truth for diarization). One engineer, one quarter. Decision gate at week 4: ship in Phase 2 or shelve until 802.11bf is mainstream.
3. **Phase 3 (2028+):** Productize. Pick A1 (auto-trigger) or B1 (eldercare) based on which the pilot proves. Differentiated on the in-Tashkent model-serving stack we're already building for STT.

## Strategic recommendation

For Omnisense's current 12-month roadmap, the answer is **not yet, but track it deliberately**.

Three concrete moves:

1. **Insert a research footnote into the development plan.** Discoverable for the team and for investors.
2. **Add a paragraph to the data-residency doc.** Honest acknowledgment that this surveillance vector exists and that Omnisense's audio-residency story doesn't address it. This *strengthens* the privacy positioning, doesn't weaken it.
3. **Buy 5× ESP32-S3-DevKitC + esp-csi** ($75 via AliExpress to Tashkent) before end of Q3. Park them. When Phase-1 is stable and one engineer-quarter is free, run the A2 feasibility study.

What this avoids: investor-deck-driven feature creep that pulls focus from getting the Phase-0 audio loop into the demo investor's hands.

What this enables: when a competitor or investor asks "but what about Wi-Fi sensing?", you have a research doc, a pilot plan, and hardware ordered. Demonstrates depth.

## Source material

- **KIT / KASTEL press release, 2025** — Wi-Fi networks as comprehensive surveillance infrastructure (197-person identification study). https://www.kit.edu
- **MIT CSAIL RF-Pose, 2018** — Zhao et al., "Through-Wall Human Pose Estimation Using Radio Signals." https://news.mit.edu/2018/artificial-intelligence-senses-people-through-walls-0612
- **DensePose from WiFi, 2022** — Geng et al., arXiv:2301.00250
- **Karl Woodbridge & Kevin Chetty (UCL), 2012** — original through-wall Wi-Fi sensing demonstration. Covered on Hackaday: https://hackaday.com/2012/08/11/
- **IEEE 802.11bf, 2025** — Wi-Fi sensing protocol. NIST overview: https://www.nist.gov/publications/ieee-80211bf
- **IEEE 802.11ac (Wi-Fi 5), 2013** — introduced BFI feedback unencrypted by design.

Open-source tooling for in-house prototyping:

- **esp-csi** (Espressif): https://github.com/espressif/esp-csi
- **Nexmon CSI** (Broadcom chipsets): https://github.com/seemoo-lab/nexmon_csi
- **Atheros CSI Tool**: https://wands.sg/research/wifi/AtherosCSI/

---

*Filed under Phase-3 tracked-adjacent technologies. Re-review at the end of Q1 2027, or when an investor specifically asks.*
