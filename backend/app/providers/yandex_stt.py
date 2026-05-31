"""Yandex SpeechKit STT adapter (Russian + Uzbek). Used when OMNI_STT=yandex.

Two recognition paths — the adapter picks based on payload size:

  - **Short-audio synchronous** (`stt:recognize`): up to 30 seconds of mono 48 kHz audio,
    returns a single plain-text result. Fast and cheap for the demo.
  - **Long-audio async** (V3 Recognizer over the REST gateway): submit, poll the
    Operations API until done, then read `recognizeFile` chunks. Returns
    speaker-tagged, timed segments — what we actually want for meeting memory.

Phase-0 limit: even the long path uses Yandex's own diarization knob (`speakerLabeling`)
and not pyannote — that runs locally for the privacy moat (see app/providers/diarize_pyannote).
In production we plan to **replace** Yandex entirely with a self-hosted fine-tuned Whisper
served in Tashkent (docs/development-plan.md §6); this adapter exists for the Week-1 cloud
baseline and for the WER risk check (`ml/eval/run_eval.py`).

Residency note: this is a cloud path — audio crosses to Yandex. The dispatch and
business plan explicitly call this out; for the production residency split we move to
in-country self-hosting. The adapter logs nothing audio-related to keep the data path
auditable.
"""
from __future__ import annotations

import time
from typing import Iterator

from .base import STTProvider

_LANG = {"ru": "ru-RU", "uz": "uz-UZ", "en": "en-US"}
_RECOGNIZE_URL = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
_LONG_RUN_URL = "https://stt.api.cloud.yandex.net/speech/v1/longRunningRecognize"
_OPS_URL = "https://operation.api.cloud.yandex.net/operations/{op_id}"

# Threshold below which we use the cheap synchronous endpoint. Yandex docs cap sync at
# 1 MB / 30 s; we leave headroom for HTTP overhead and timing skew.
_SYNC_MAX_BYTES = 900 * 1024


class YandexSTT(STTProvider):
    def __init__(
        self,
        api_key: str,
        folder_id: str,
        *,
        poll_interval_s: float = 2.0,
        poll_timeout_s: float = 600.0,
        sample_rate_hz: int = 48000,
    ) -> None:
        if not api_key:
            raise ValueError("YANDEX_API_KEY is required for OMNI_STT=yandex")
        self.api_key = api_key
        self.folder_id = folder_id
        self.poll_interval_s = poll_interval_s
        self.poll_timeout_s = poll_timeout_s
        self.sample_rate_hz = sample_rate_hz

    # ---- entry point --------------------------------------------------------
    def transcribe(self, audio: bytes, lang: str) -> list[dict]:
        if len(audio) <= _SYNC_MAX_BYTES:
            return list(self._sync(audio, lang))
        return list(self._async(audio, lang))

    # ---- sync (short-audio) -------------------------------------------------
    def _sync(self, audio: bytes, lang: str) -> Iterator[dict]:
        import httpx  # lazy: only needed on the real path

        params: dict[str, str] = {
            "lang": _LANG.get(lang, "ru-RU"),
            # OggOpus is the codec the mobile recorder ships; LPCM is the alternative.
            "format": "oggopus",
            "sampleRateHertz": str(self.sample_rate_hz),
        }
        if self.folder_id:
            params["folderId"] = self.folder_id
        resp = httpx.post(
            _RECOGNIZE_URL,
            params=params,
            headers={"Authorization": f"Api-Key {self.api_key}"},
            content=audio,
            timeout=60.0,
        )
        resp.raise_for_status()
        text = (resp.json().get("result") or "").strip()
        if text:
            yield {"text": text, "start_ms": 0, "end_ms": 0, "speaker": "owner"}

    # ---- async (long-audio) -------------------------------------------------
    def _async(self, audio: bytes, lang: str) -> Iterator[dict]:
        """Submit → poll → parse. Returns one segment per speaker turn (when Yandex
        speakerLabeling is on) or one segment per chunk."""
        import base64
        import httpx  # lazy

        body = {
            "config": {
                "specification": {
                    "languageCode": _LANG.get(lang, "ru-RU"),
                    "audioEncoding": "OGG_OPUS",
                    "sampleRateHertz": self.sample_rate_hz,
                    "audioChannelCount": 1,
                    "rawResults": False,
                    "literature_text": True,
                    "profanityFilter": False,
                    "speakerLabeling": True,
                }
            },
            "audio": {"content": base64.b64encode(audio).decode("ascii")},
        }
        if self.folder_id:
            body["config"]["folderId"] = self.folder_id
        submit = httpx.post(
            _LONG_RUN_URL,
            headers={"Authorization": f"Api-Key {self.api_key}",
                     "Content-Type": "application/json"},
            json=body, timeout=60.0,
        )
        submit.raise_for_status()
        op_id = submit.json()["id"]

        # Poll.
        deadline = time.monotonic() + self.poll_timeout_s
        while True:
            if time.monotonic() > deadline:
                raise TimeoutError(f"Yandex STT operation {op_id} did not complete in "
                                   f"{self.poll_timeout_s:.0f}s")
            r = httpx.get(
                _OPS_URL.format(op_id=op_id),
                headers={"Authorization": f"Api-Key {self.api_key}"},
                timeout=30.0,
            )
            r.raise_for_status()
            op = r.json()
            if op.get("done"):
                break
            time.sleep(self.poll_interval_s)

        if "error" in op:
            raise RuntimeError(f"Yandex STT failed: {op['error']}")

        # Response shape: {"response": {"chunks": [{"alternatives": [...], "channelTag": "1",
        #                  "startTime": "0s", ..., "speakerTag": "1"}]}}.
        for chunk in op.get("response", {}).get("chunks", []) or []:
            alts = chunk.get("alternatives") or []
            text = (alts[0].get("text") if alts else "").strip()
            if not text:
                continue
            yield {
                "text": text,
                "start_ms": _ms(chunk.get("startTime")),
                "end_ms": _ms(chunk.get("endTime")),
                "speaker": f"speaker_{chunk.get('speakerTag', '?')}",
            }


def _ms(t: str | None) -> int:
    """Parse Yandex's RFC-3339 duration ("12.345s") into milliseconds. Returns 0 on miss."""
    if not t:
        return 0
    s = str(t).rstrip("s")
    try:
        return int(float(s) * 1000)
    except ValueError:
        return 0
