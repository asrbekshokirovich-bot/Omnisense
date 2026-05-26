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


class Diarizer(ABC):
    """Speaker diarization. Two responsibilities:

    1) Split a recording into speaker turns: list of {start_ms, end_ms, speaker_label,
       voiceprint}. The speaker_label is local to the clip (e.g. "SPEAKER_00").
    2) Embed a short reference clip as a voiceprint, so an "owner enrollment" can decide
       which local speaker_label belongs to the device owner.

    Privacy: voiceprints + raw audio stay in-country per the residency plan. The diarizer
    never sees the LLM and the LLM never sees the voiceprint.
    """

    @abstractmethod
    def diarize(self, audio: bytes) -> list[dict]:
        """Return turns: {start_ms, end_ms, speaker_label, voiceprint: list[float]}."""

    @abstractmethod
    def embed_voice(self, audio: bytes) -> list[float]:
        """Return a single voiceprint vector for a reference clip (used by enrollment)."""

    @property
    @abstractmethod
    def dim(self) -> int:
        """Dimensionality of the voiceprint vectors this diarizer returns."""
