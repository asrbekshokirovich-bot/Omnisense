"""OpenAI-compatible embeddings + chat adapter (works with OpenAI, Azure, or a self-hosted
gateway). Used when OMNI_EMBED=openai / OMNI_LLM=openai.

Note on residency: this is a CROSS-BORDER text path. Per the Uzbekistan plan, only derived
TEXT may leave the country and only with consent; voice/voiceprints stay in-country. At
scale, swap this for a self-hosted open LLM in Tashkent (see docs/development-plan.md).
"""
from __future__ import annotations

import json

from .base import EmbeddingProvider, LLMProvider

_LANG_NAME = {"ru": "Russian", "uz": "Uzbek", "en": "English"}


class _Client:
    def __init__(self, api_key: str, base_url: str) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for the openai provider")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _post(self, path: str, payload: dict) -> dict:
        import httpx  # lazy

        resp = httpx.post(
            f"{self.base_url}{path}",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.json()


class OpenAIEmbedding(EmbeddingProvider):
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.client = _Client(api_key, base_url)
        self.model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        data = self.client._post("/embeddings", {"model": self.model, "input": texts})
        return [row["embedding"] for row in data["data"]]


class OpenAILLM(LLMProvider):
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.client = _Client(api_key, base_url)
        self.model = model

    def _chat(self, system: str, user: str, json_mode: bool = False) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        data = self.client._post("/chat/completions", payload)
        return data["choices"][0]["message"]["content"]

    def answer(self, question: str, context: list[dict], lang: str) -> str:
        lang_name = _LANG_NAME.get(lang, "the user's language")
        ctx = "\n".join(
            f'- [{c.get("timestamp","?")}] {c.get("speaker","?")}: {c["text"]}' for c in context
        )
        system = (
            f"You are Omnisense, a personal-memory assistant. Answer ONLY from the provided "
            f"memory excerpts. Reply in {lang_name}. Cite the speaker and timestamp. If the "
            f"answer isn't in the memory, say so."
        )
        return self._chat(system, f"Question: {question}\n\nMemory excerpts:\n{ctx}")

    def summarize_day(self, segments: list[dict], lang: str) -> dict:
        lang_name = _LANG_NAME.get(lang, "the user's language")
        joined = "\n".join(f'- {s["text"]}' for s in segments)
        system = (
            f"You are Omnisense. Summarize the day's captured conversations in {lang_name}. "
            f'Return strict JSON with keys: summary (string), decisions (string[]), '
            f"action_items (string[]), key_quotes (string[])."
        )
        raw = self._chat(system, joined, json_mode=True)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"summary": raw, "decisions": [], "action_items": [], "key_quotes": []}
