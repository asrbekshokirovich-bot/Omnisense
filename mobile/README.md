# mobile — Omnisense app (Phase 0 shell)

A minimal **Flutter** app with three screens (Capture / Ask / Briefing) over the backend
API. **Capture records from the microphone** (default-off — only on tap) and uploads to
`/ingest/audio`, with a text-paste fallback for the offline mock STT. Background capture +
BLE pendant streaming land in Phase 1.

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
  <!-- Phase 1 (background capture): FOREGROUND_SERVICE, FOREGROUND_SERVICE_MICROPHONE -->
  ```
- **iOS** — `ios/Runner/Info.plist`: `NSMicrophoneUsageDescription` = why you record.

## Structure
- `lib/api.dart` — API client (ingest text, upload audio, ask, briefing, delete).
- `lib/capture.dart` — record + upload (and text fallback).
- `lib/main.dart` — three-tab UI with RU/UZ/EN toggle.

## Roadmap (Phase 1)
Background recording (foreground service), Silero VAD on-device, BLE pendant streaming,
consent UI + recording indicator, encrypted local buffer, one-tap delete. Android-first
(the Uzbek market skews budget Android).
