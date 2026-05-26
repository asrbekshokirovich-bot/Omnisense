"""Provider interfaces. The app depends on these, never on a concrete vendor — so we can
swap cloud (demo) for self-hosted/in-country (production) without touching the pipeline."""
from __future__ import annotations

from abc import ABC, abstractmethod


class STTProvider(ABC):
    @abstractmethod
    def transcribe(self, audio: bytes, lang: str) -> list[dict]:
        """Return a list of {text, start_ms, end_ms, speaker} segments."""


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text."""

    @property
    @abstractmethod
    def dim(self) -> int:
        """The dimensionality of the vectors this provider returns.

        The pgvector schema is sized to this. Mismatching dims across providers in the same
        database breaks search, so changing the embedder normally means wiping the store.
        """


class LLMProvider(ABC):
    @abstractmethod
    def answer(self, question: str, context: list[dict], lang: str) -> str:
        """Answer a question grounded in retrieved context segments."""

    @abstractmethod
    def summarize_day(self, segments: list[dict], lang: str) -> dict:
        """Return {summary, decisions[], action_items[], key_quotes[]} for a day's segments."""
