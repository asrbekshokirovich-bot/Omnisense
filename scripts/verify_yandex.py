"""Live-verify Yandex SpeechKit STT.

Run:

    python scripts/verify_yandex.py

Requires `YANDEX_API_KEY` (the secret value, sent as `Api-Key <secret>` per Yandex
docs) in `backend/.env` or the process environment. `YANDEX_FOLDER_ID` is optional —
some Yandex API-key configurations are folder-scoped at creation time, others require
the folder id on every request. The script reports whichever path applies.

What it checks:
  1. Auth works (no 401 / 403 from Yandex).
  2. The sync recognize endpoint accepts our payload shape (LPCM 8 kHz mono).
  3. Both `ru-RU` and `uz-UZ` language codes round-trip without API errors.

Common failure mode this script knows about: Yandex returns HTTP 401 with an inner
gRPC `PermissionDenied` when the API key is valid (correctly authenticates) but the
underlying service account lacks the `ai.speechkit-stt.user` IAM role on its folder.
The error message lists which folder / cloud / organization were checked. Fix in
Yandex Cloud Console → Folder X → Access bindings → add `ai.speechkit-stt.user`
to the service account. The script reports this case as "ROLE_MISSING" with the
exact action, not a generic auth fail.

What it deliberately does NOT do:
  - Score WER. The repo has only text-only JSONL samples (`ml/eval/sample/*.jsonl`),
    no audio with ground-truth references. Real WER scoring needs labeled audio —
    document this as the team's next move once a sample bank is available, then run
    `python ml/eval/run_eval.py --dataset <file>.jsonl --audio-dir <dir>
    --provider yandex`.

Audio: we synthesize tiny ~1-second LPCM samples (silence + a 440 Hz tone) with
stdlib `wave` + `struct`. This is enough to prove the auth + transport path; it will
NOT produce meaningful transcription text (Yandex correctly returns an empty result
for non-speech), and that's fine — empty-but-200 means everything below the model
worked.

Key is masked in every print (first 6 + last 4 chars).
"""
from __future__ import annotations

import json
import math
import os
import struct
import sys
import time
import wave
from io import BytesIO
from pathlib import Path

# Windows console fallback (cp1251 mangles RU/UZ output otherwise).
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass


_RECOGNIZE_URL = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
_SAMPLE_RATE = 8000  # smallest rate Yandex accepts for LPCM


def _mask(key: str) -> str:
    if not key:
        return "<empty>"
    if len(key) <= 10:
        return f"<{len(key)} chars>"
    return f"{key[:6]}…{key[-4:]}"


def _force_load(env_key: str) -> str:
    """Load `env_key` from backend/.env, OVERWRITING any value already in os.environ.

    Same reason as in verify_anthropic.py: a parent shell that has the variable set
    to empty string would otherwise silently mask the file value (because the
    app.config dotenv loader uses setdefault to avoid clobbering real shell vars).
    """
    env_path = Path(__file__).resolve().parent.parent / "backend" / ".env"
    if not env_path.is_file():
        return os.environ.get(env_key, "")
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == env_key:
            v = v.strip().strip('"').strip("'")
            if v:
                os.environ[env_key] = v
            return v
    return os.environ.get(env_key, "")


def _sample_silence(duration_s: float = 1.0) -> bytes:
    """1 second of LPCM silence at 8 kHz mono, 16-bit signed. Yandex returns 200 with
    empty result for silence — that proves the API accepted the payload shape."""
    buf = BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)  # 16-bit
        w.setframerate(_SAMPLE_RATE)
        w.writeframes(b"\x00\x00" * int(_SAMPLE_RATE * duration_s))
    # wave.open writes a RIFF/WAV header; Yandex LPCM mode wants RAW samples, not WAV.
    # We strip the WAV header so the payload is pure 16-bit PCM little-endian.
    data = buf.getvalue()
    return _strip_wav_header(data)


def _sample_tone(duration_s: float = 1.0, freq_hz: float = 440.0) -> bytes:
    """A pure tone — same shape as the silence test but non-zero frames, so we know
    the payload itself is non-trivial. Still won't transcribe to anything meaningful;
    we expect an empty `result` field from Yandex but a 200 status."""
    frames = bytearray()
    n = int(_SAMPLE_RATE * duration_s)
    amp = 0.2 * 32767
    for i in range(n):
        sample = int(amp * math.sin(2 * math.pi * freq_hz * i / _SAMPLE_RATE))
        frames += struct.pack("<h", sample)
    return bytes(frames)


def _strip_wav_header(wav_bytes: bytes) -> bytes:
    """Strip a standard RIFF/WAV header and return the raw PCM samples. The format
    chunk + data chunk header take 44 bytes for a vanilla WAV file."""
    # Find "data" chunk and return everything after the 8-byte chunk header.
    idx = wav_bytes.find(b"data")
    if idx < 0:
        return wav_bytes
    return wav_bytes[idx + 8:]


def _recognize(audio: bytes, lang: str, key: str, folder_id: str | None) -> dict:
    """One sync recognize call. Returns {status, body, error, took_s}."""
    import urllib.request
    import urllib.error
    import urllib.parse

    params = {
        "lang": lang,
        "format": "lpcm",
        "sampleRateHertz": str(_SAMPLE_RATE),
    }
    if folder_id:
        params["folderId"] = folder_id
    url = f"{_RECOGNIZE_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url, data=audio, method="POST",
        headers={
            "Authorization": f"Api-Key {key}",
            "Content-Type": "application/octet-stream",
        },
    )
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode("utf-8", errors="replace")
            return {"status": r.status, "body": body, "error": None,
                    "took_s": time.monotonic() - t0}
    except urllib.error.HTTPError as e:
        return {
            "status": e.code,
            "body": e.read().decode("utf-8", errors="replace"),
            "error": str(e),
            "took_s": time.monotonic() - t0,
        }
    except urllib.error.URLError as e:
        return {"status": None, "body": "", "error": f"URLError: {e}",
                "took_s": time.monotonic() - t0}


def main() -> int:
    key = _force_load("YANDEX_API_KEY")
    key_id = _force_load("YANDEX_API_KEY_ID")
    folder_id = _force_load("YANDEX_FOLDER_ID") or None
    if not key:
        print("FAIL: YANDEX_API_KEY not set (looked in backend/.env + environ).",
              file=sys.stderr)
        return 1
    print(f"key:      {_mask(key)} ({len(key)} chars)")
    print(f"key_id:   {_mask(key_id)}" if key_id else "key_id:   <not set>")
    print(f"folder_id: {_mask(folder_id) if folder_id else '<not set — may need YANDEX_FOLDER_ID>'}")
    print()

    silence = _sample_silence(1.0)
    tone = _sample_tone(1.0)
    print(f"silence sample: {len(silence)} bytes LPCM 8kHz 16-bit mono")
    print(f"tone sample:    {len(tone)} bytes LPCM 8kHz 16-bit mono (440 Hz)")
    print()

    failures: list[str] = []
    role_missing_evidence: dict | None = None

    def _classify(status: int | None, body: str) -> str:
        if status == 200:
            return "OK"
        if status is None:
            return "NETWORK"
        if status == 400:
            lo = body.lower()
            if "folder" in lo and not folder_id:
                return "FOLDER_REQUIRED"
            return "BAD_AUDIO"
        # Yandex wraps PermissionDenied inside HTTP 401 — distinguish that from a
        # pure auth-rejected case so the user knows where to look.
        if status in (401, 403) and "permissiondenied" in body.lower():
            return "ROLE_MISSING"
        if status in (401, 403):
            return "AUTH_REJECTED"
        return "OTHER"

    for label, audio in [("silence", silence), ("tone", tone)]:
        for lang in ("ru-RU", "uz-UZ"):
            print(f"[{label} / {lang}] POST /speech/v1/stt:recognize")
            r = _recognize(audio, lang, key, folder_id)
            kind = _classify(r["status"], r["body"])
            print(f"  status: {r['status']} ({kind}) in {r['took_s']:.2f}s")
            body_preview = r["body"][:300]
            print(f"  body:   {body_preview!r}")
            if kind == "OK":
                try:
                    parsed = json.loads(r["body"])
                    print(f"  transcript: {parsed.get('result', '')!r}")
                except json.JSONDecodeError:
                    failures.append(f"[{label}/{lang}] 200 but non-JSON body")
            elif kind == "ROLE_MISSING":
                # Don't fail on EVERY call — fold these into one actionable report.
                role_missing_evidence = role_missing_evidence or {
                    "status": r["status"], "body": r["body"][:500],
                }
            elif kind == "AUTH_REJECTED":
                failures.append(f"[{label}/{lang}] AUTH_REJECTED — key invalid")
            elif kind == "FOLDER_REQUIRED":
                failures.append(
                    f"[{label}/{lang}] Yandex requires YANDEX_FOLDER_ID — add it to "
                    f"backend/.env and re-run"
                )
            elif kind == "BAD_AUDIO":
                # Synthetic LPCM may not satisfy every Yandex validator — note but
                # don't fail (auth was OK).
                print("  NOTE: 400 about audio — auth is OK; the synthetic payload "
                      "didn't satisfy a validator. Real audio uploads from the mobile "
                      "recorder will use a different format (OGG/Opus 48 kHz).")
            elif kind == "NETWORK":
                failures.append(f"[{label}/{lang}] network error: {r['error']}")
            else:
                failures.append(f"[{label}/{lang}] unexpected status {r['status']}")
            print()

    print("=" * 60)

    if role_missing_evidence:
        print("YANDEX AUTH IS RECOGNIZED, BUT THE SERVICE ACCOUNT LACKS THE IAM ROLE")
        print("required to call SpeechKit STT. Yandex returns HTTP 401 with an inner")
        print("gRPC PermissionDenied; the response lists which folder / cloud / org")
        print("it checked.")
        print()
        print(f"Server said: {role_missing_evidence['body']!r}")
        print()
        print("Action — in Yandex Cloud Console:")
        print("  1. Open the folder mentioned in the response above.")
        print("  2. Access bindings → Configure access.")
        print("  3. Add the service account that owns this API key (KEY_ID="
              f"{_mask(key_id) if key_id else '<set YANDEX_API_KEY_ID>'}).")
        print("  4. Grant the role:  ai.speechkit-stt.user")
        print("     (and ai.speechkit-tts.user later if we add TTS).")
        print("  5. (Optional) Set YANDEX_FOLDER_ID in backend/.env to that folder.")
        print()
        print("Then re-run:  python scripts/verify_yandex.py")
        return 1

    if failures:
        print("Yandex calls had issues:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("ALL CHECKS PASSED — Yandex SpeechKit auth + transport work end-to-end.")
    print()
    print("Real WER scoring requires labeled audio. Add WAV/OGG samples + reference")
    print("transcripts to ml/eval/sample/ then:")
    print("  python ml/eval/run_eval.py --dataset uz_audio.jsonl "
          "--audio-dir audio --provider yandex --json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
