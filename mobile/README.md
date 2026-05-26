# mobile — Omnisense app (Phase 0 shell)

A minimal **Flutter** app with four screens (Capture / Ask / Briefing / Settings) over the
backend API. **Capture records from the microphone** (default-off — only on tap) and
uploads to `/ingest/audio`, with a text-paste fallback for the offline mock STT.

Background capture + BLE pendant streaming land in Phase 1 — see
[`../docs/mobile-background-capture.md`](../docs/mobile-background-capture.md).

> Not compiled in CI yet — needs the Flutter SDK. Generate platform folders first:
> `flutter create .` (run inside `mobile/`), then add the permissions below.

## Run
```bash
cd mobile
flutter create .            # generates android/ ios/ etc. (first time only)
flutter pub get
# Android emulator reaches the host backend at 10.0.2.2:
flutter run --dart-define=OMNI_API=http://10.0.2.2:8000
```
(Start the backend first — see `../backend/README.md`.)

## Required permissions (add after `flutter create .`)
- **Android** — `android/app/src/main/AndroidManifest.xml`:
  ```xml
  <uses-permission android:name="android.permission.RECORD_AUDIO"/>
  <uses-permission android:name="android.permission.INTERNET"/>
  <!-- Phase 1 (background capture): FOREGROUND_SERVICE, FOREGROUND_SERVICE_MICROPHONE,
       POST_NOTIFICATIONS, WAKE_LOCK -->
  ```
- **iOS** — `ios/Runner/Info.plist`: `NSMicrophoneUsageDescription` = why you record.

## Structure
- `lib/api.dart` — API client (ingest text, upload audio, ask, briefing, usage, delete).
  Sends `X-User-Id` so the backend can keep tenants isolated.
- `lib/capture.dart` — record + upload (and text fallback), with a pulsing red
  "Recording" indicator that is visible only while the mic is live.
- `lib/consent.dart` — first-launch consent screen (the privacy pitch + a toggle for
  cross-border AI). Persisted to a small JSON file. Revoked from Settings.
- `lib/tenant.dart` — per-install random tenant id, persisted to a small text file.
- `lib/main.dart` — four-tab UI with RU/UZ/EN toggle and a Settings tab (usage
  counters, one-tap delete, forget-this-device, revoke consent).

## Privacy by construction
- **Default-OFF.** No mic until the user taps Record on the Capture screen.
- **Visible indicator.** Pulsing red pill is visible whenever audio is being captured.
- **One-tap delete.** Settings → "Delete my memory" calls `DELETE /data` on the
  backend for THIS tenant.
- **Forget device.** Settings → "Forget this device" wipes the local tenant id; the
  next launch is a brand-new tenant on the server.
- **Revoke consent.** Settings → re-onboard. Drops back to the consent screen.

## Roadmap (Phase 1)
Background recording (foreground service), Silero VAD on-device, BLE pendant streaming,
encrypted local buffer, deferred upload on unmetered Wi-Fi. Android-first (the Uzbek
market skews budget Android). See
[`../docs/mobile-background-capture.md`](../docs/mobile-background-capture.md).
