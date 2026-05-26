"""Offline providers so the full loop runs with no API keys and no network.

- MockSTT treats an uploaded file as a UTF-8 transcript (so you can "ingest" a .txt of a
  meeting) and splits it into pseudo-timed, speaker-tagged segments. Real audio decoding is
  the job of a real STT provider.
- HashingEmbedding is a deterministic bag-of-tokens vector (works for RU/UZ/EN). It is a
  PLUMBING stub — semantically weak — swapped for BGE-M3 / OpenAI in real runs.
- MockLLM answers extractively (quotes the best-matching memory with its citation) and
  builds a heuristic daily briefing. A real LLM produces far better prose.
"""
from __future__ import annotations

import hashlib
import math
import re

from .base import EmbeddingProvider, LLMProvider, STTProvider

_TOKEN = re.compile(r"\w+", re.UNICODE)
_ACTION_HINTS = (
    # en / ru / uz cues that a sentence is a commitment or task
    "will ", "need to", "should", "let's", "todo", "to do", "by friday", "deadline",
    "должен", "нужно", "надо", "договорились", "сделаю", "дедлайн",
    "kerak", "qilaman", "qilamiz", "kelishdik", "muddat",
)
_DECISION_HINTS = ("decide", "agreed", "agree", "решили", "договорились", "qaror", "kelishdik")


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class HashingEmbedding(EmbeddingProvider):
    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            vec = [0.0] * self.dim
            for tok in _tokens(text):
                h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
                vec[h % self.dim] += 1.0 if (h >> 8) & 1 else -1.0
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            out.append([x / norm for x in vec])
        return out


class MockSTT(STTProvider):
    def transcribe(self, audio: bytes, lang: str) -> list[dict]:
        try:
            text = audio.decode("utf-8")
        except UnicodeDecodeError:
            text = "[mock STT: binary audio received — plug in a real STT provider to transcribe]"
        # One segment per non-empty line; alternate owner/other; fake ~6s spacing.
        segments: list[dict] = []
        t = 0
        speakers = ("owner", "speaker_2")
        for i, line in enumerate(l.strip() for l in text.splitlines()):
            if not line:
                continue
            segments.append({
                "text": line,
                "start_ms": t,
                "end_ms": t + 6000,
                "speaker": speakers[i % 2],
            })
            t += 6000
        if not segments and text.strip():
            segments.append({"text": text.strip(), "start_ms": 0, "end_ms": 6000, "speaker": "owner"})
        return segments


class MockLLM(LLMProvider):
    def answer(self, question: str, context: list[dict], lang: str) -> str:
        if not context:
            return _t(lang,
                      en="I couldn't find anything about that in your memory yet.",
                      ru="Я пока не нашёл это в вашей памяти.",
                      uz="Hozircha xotirangizdan buni topa olmadim.")
        top = context[0]
        lead = _t(lang,
                  en="Based on your memory",
                  ru="По вашим записям",
                  uz="Xotirangizga ko'ra")
        return f'{lead} — "{top["text"]}" ({top.get("speaker", "?")}, {top.get("timestamp", "?")}).'

    def summarize_day(self, segments: list[dict], lang: str) -> dict:
        texts = [s["text"] for s in segments]
        actions = [t for t in texts if any(h in t.lower() for h in _ACTION_HINTS)]
        decisions = [t for t in texts if any(h in t.lower() for h in _DECISION_HINTS)]
        summary = _t(lang,
                     en=f"{len(segments)} moments captured across the day.",
                     ru=f"За день сохранено {len(segments)} фрагментов.",
                     uz=f"Kun davomida {len(segments)} lahza saqlandi.")
        return {
            "summary": summary,
            "decisions": decisions[:5],
            "action_items": actions[:8],
            "key_quotes": texts[:3],
        }


def _t(lang: str, *, en: str, ru: str, uz: str) -> str:
    return {"ru": ru, "uz": uz}.get((lang or "").lower(), en)
