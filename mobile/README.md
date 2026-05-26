# mobile — Omnisense app (Phase 0 shell)

A minimal **Flutter** shell with three screens (Capture / Ask / Briefing) over the backend
API. It demonstrates the full loop today; on-device **recording + BLE pendant** capture and
background audio land in Phase 1 (the "Capture" screen currently ingests typed/pasted text).

## Run
```bash
cd mobile
flutter pub get
# Android emulator reaches the host backend at 10.0.2.2:
flutter run --dart-define=OMNI_API=http://10.0.2.2:8000
```
(Start the backend first — see `../backend/README.md`.)

## Structure
- `lib/api.dart` — thin API client.
- `lib/main.dart` — three-tab UI (Capture / Ask / Briefing) with RU/UZ/EN toggle.

## Roadmap (Phase 1)
Background audio recording (foreground service), Silero VAD on-device, BLE pendant
streaming, consent UI + recording indicator, encrypted local buffer, one-tap delete.
Android-first (the Uzbek market skews budget Android).
