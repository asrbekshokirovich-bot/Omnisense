"""Yandex SpeechKit STT adapter (Russian + Uzbek). Used when OMNI_STT=yandex.

Phase-0 scope: short-audio synchronous recognition (good for the demo). Long-audio async
recognition and speaker diarization are production follow-ups (diarization via pyannote in
the in-country pipeline). This is the cloud path; production migrates to a self-hosted,
fine-tuned Whisper served in-country (see docs/development-plan.md §6).
"""
from __future__ import annotations

from .base import STTProvider

_LANG = {"ru": "ru-RU", "uz": "uz-UZ", "en": "en-US"}
_RECOGNIZE_URL = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"


class YandexSTT(STTProvider):
    def __init__(self, api_key: str, folder_id: str) -> None:
        if not api_key:
            raise ValueError("YANDEX_API_KEY is required for OMNI_STT=yandex")
        self.api_key = api_key
        self.folder_id = folder_id

    def transcribe(self, audio: bytes, lang: str) -> list[dict]:
        import httpx  # lazy: only needed on the real path

        params = {"lang": _LANG.get(lang, "ru-RU")}
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
        text = resp.json().get("result", "").strip()
        if not text:
            return []
        # Short-audio API returns plain text without timing/speakers; one segment for now.
        return [{"text": text, "start_ms": 0, "end_ms": 0, "speaker": "owner"}]
