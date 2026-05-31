# Mobile background capture — Phase 1 plan

The Phase-0 mobile shell records **only while the Capture screen is open** and only
after the user explicitly taps "Record" (see `mobile/lib/capture.dart`). For Omnisense
to deliver on its core promise — "ask anything you said today" — capture must continue
in the background, on a budget Android phone, without burning battery and without
violating either platform's background-execution rules or Uzbekistan's privacy law.

This document is the plan for crossing that gap in Phase 1. **No background recording
ships in Phase 0.**

## Hard constraints

1. **User control comes first.** Background capture is opt-in (separate consent grant
   from foreground capture), can be paused with one tap from a persistent notification,
   and is visibly indicated whenever active (Android system mic indicator, iOS orange
   dot — both are platform-enforced when `MICROPHONE` is held).
2. **Default off.** First-run consent grants foreground capture only. The background
   toggle lives in Settings.
3. **Battery budget.** Target < 5% / 8 h on a mid-range Android (Tecno/Infinix —
   relevant for the Uzbek market). That rules out a naive always-on PCM stream.
4. **Residency.** Audio buffered on-device is encrypted at rest (Android Keystore /
   iOS Data Protection). Uploads go to the in-country backend only.

## Architecture

```
┌────────────────────────┐    PCM 16kHz mono
│ MicrophoneStream       ├────────────────────┐
│ (low-bitrate Opus)     │                    │
└──────┬─────────────────┘                    │
       │                                      ▼
       │                            ┌─────────────────────┐
       │            speech frames?  │ Silero VAD on-device│  YES → enqueue chunk
       │  (yes/no on 30-ms frames)  │  (tiny ONNX model)  │  NO  → drop
       └────────────────────────────►                     │
                                    └─────────┬───────────┘
                                              │
                                              ▼
                                      ┌──────────────┐
                                      │ Encrypted    │
                                      │ ring buffer  │   ≤ 5 min at a time
                                      │ (file-based) │
                                      └──────┬───────┘
                                             │
                                             ▼   (Wi-Fi or unmetered)
                              ┌─────────────────────────────┐
                              │ Upload worker (WorkManager / │
                              │ BGTaskScheduler) → /ingest/  │
                              │ audio with X-User-Id          │
                              └─────────────────────────────┘
```

- **Silero VAD on-device** (a few MB ONNX, runs comfortably on CPU) drops silence —
  cuts upload volume and battery by an order of magnitude.
- **5-minute encrypted chunks**, not a continuous stream, so a crash, a
  Doze-mode kick, or a flaky upload only loses the current window.
- **Upload is deferred** to unmetered Wi-Fi when possible, since Uzbek mobile data is
  not free.

## Android

- Foreground service of type **`microphone`** (Android 14 requirement). Persistent
  notification shows: status (Recording / Paused / Uploading), the day's segment
  count, and a Pause button.
- Permissions to add to `android/app/src/main/AndroidManifest.xml`:
  ```xml
  <uses-permission android:name="android.permission.RECORD_AUDIO"/>
  <uses-permission android:name="android.permission.FOREGROUND_SERVICE"/>
  <uses-permission android:name="android.permission.FOREGROUND_SERVICE_MICROPHONE"/>
  <uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>
  <uses-permission android:name="android.permission.WAKE_LOCK"/>
  ```
- Use **WorkManager** for chunk uploads with `setRequiredNetworkType(UNMETERED)`
  unless the user opts into "upload on mobile data".
- **Battery-optimization exemption** is a sharp edge — request it only after the user
  has used the app for 7+ days, framed as "keep Omnisense reliable in the background".
- **Doze mode**: design for being killed periodically; the ring buffer + chunked
  upload + idempotent ingest (segment id is uuid4 client-side) makes this safe.

## iOS

- iOS does not allow truly indefinite background mic capture. Two options:
  - **Background mode = `audio`** keeps the mic alive when the app is suspended, but
    requires the user to start a recording session in foreground first — matches our
    consent flow.
  - **CallKit / VoIP-style** (not appropriate for memory capture; would mislead users).
- **`BGTaskScheduler`** handles deferred uploads.
- `Info.plist`:
  ```xml
  <key>NSMicrophoneUsageDescription</key>
  <string>Omnisense records conversations only while you have it on, so you can ask
   questions about them later.</string>
  <key>UIBackgroundModes</key>
  <array>
    <string>audio</string>
    <string>fetch</string>
    <string>processing</string>
  </array>
  ```

## BLE pendant (the dedicated audio wearable from the business plan)

- Phase 1 still uses the phone mic. The pendant streams via **A2DP / Bluetooth Low
  Energy audio (LE Audio)** once available; falls back to "press button on pendant,
  pendant records locally, syncs over BLE when in range".
- **Pairing flow** lives in Settings → Devices. The pendant carries an Omnisense
  certificate so we can drop foreign clones server-side.

## Privacy gates the user sees while it runs

- **Foreground capture (already shipped, Phase 0):** red dot + "Recording" pill on
  the Capture screen while the mic is active.
- **Background capture (Phase 1):** persistent system notification with the same red
  dot, plus the platform-enforced mic indicator (Android 12+ green dot, iOS orange).
- **One-tap pause** from the notification, and **one-tap delete-all** from Settings →
  Privacy (already shipped — wired to `DELETE /data`).

## Test plan

1. **Battery / hour idle**, 1 hour conversation, 8 hour mixed — on a Tecno Spark and a
   mid-2024 Samsung A-series. Compare to baseline (mic permission denied).
2. **Doze + App Standby**: force the device into Doze with `adb shell dumpsys deviceidle force-idle`,
   verify chunks land on next maintenance window.
3. **Killed during upload**: kill the process mid-upload, restart, verify the buffered
   chunks resume (idempotent ingest covers this).
4. **Permission revoked at runtime**: verify the foreground service drops cleanly and
   the persistent notification disappears without crashing the app.

## What this plan deliberately does NOT do

- **No continuous transcript streaming to backend.** Chunked uploads only. Live
  streaming costs too much battery and bandwidth, and provides no UX win for our
  "ask later" model.
- **No on-device LLM.** Phase 1 keeps STT cloud (Yandex → fine-tuned Whisper in
  Tashkent), embeddings local or in-country, LLM cross-border with consent. On-device
  LLM is a Phase 2+ research item.
- **No Always-On Display recording indicators.** Platform indicators already exist;
  shipping our own would be ignored by users at best, distrust-building at worst.
