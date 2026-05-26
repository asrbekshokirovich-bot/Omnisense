"""Anthropic (Claude) LLM adapter — answers + daily briefings. Used when OMNI_LLM=anthropic.

Default model is Claude Haiku (fast + cheap, good multilingual incl. Russian/Uzbek). This is
a cross-border TEXT path (voice/voiceprints stay in-country); enable only with user consent.
"""
from __future__ import annotations

import json
import re

from .base import LLMProvider

_API = "https://api.anthropic.com/v1/messages"
_LANG_NAME = {"ru": "Russian", "uz": "Uzbek", "en": "English"}
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class AnthropicLLM(LLMProvider):
    def __init__(self, api_key: str, model: str, version: str = "2023-06-01") -> None:
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for OMNI_LLM=anthropic")
        self.api_key = api_key
        self.model = model
        self.version = version

    def _message(self, system: str, user: str, max_tokens: int = 1024) -> str:
        import httpx  # lazy: only needed on the real path

        resp = httpx.post(
            _API,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": self.version,
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        blocks = resp.json().get("content", [])
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()

    def answer(self, question: str, context: list[dict], lang: str) -> str:
        if not context:
            return self._message(
                "You are Omnisense, a personal-memory assistant.",
                f"Reply in {_LANG_NAME.get(lang, 'the user language')} that there is nothing "
                f"in memory about: {question}",
            )
        lang_name = _LANG_NAME.get(lang, "the user's language")
        ctx = "\n".join(
            f'- [{c.get("timestamp","?")}] {c.get("speaker","?")}: {c["text"]}' for c in context
        )
        system = (
            f"You are Omnisense, a personal-memory assistant. Answer ONLY from the provided "
            f"memory excerpts. Reply in {lang_name}, briefly. Cite the speaker and timestamp. "
            f"If the answer isn't in the memory, say so."
        )
        return self._message(system, f"Question: {question}\n\nMemory excerpts:\n{ctx}")

    def summarize_day(self, segments: list[dict], lang: str) -> dict:
        lang_name = _LANG_NAME.get(lang, "the user's language")
        joined = "\n".join(f'- {s["text"]}' for s in segments) or "(no memories today)"
        system = (
            f"You are Omnisense. Summarize the day's captured conversations in {lang_name}. "
            f"Return ONLY a JSON object with keys: summary (string), decisions (string[]), "
            f"action_items (string[]), key_quotes (string[]). No prose outside the JSON."
        )
        raw = self._message(system, joined, max_tokens=1024)
        match = _JSON_RE.search(raw)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {"summary": raw, "decisions": [], "action_items": [], "key_quotes": []}
