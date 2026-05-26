"""Split a transcript into retrieval-sized chunks. Sentence-aware, with a soft length cap."""
from __future__ import annotations

import re

# Sentence boundaries for Latin + Cyrillic text (Uzbek is Latin-script; Russian is Cyrillic).
_SENT = re.compile(r"(?<=[.!?…])\s+")


def split_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    return [s.strip() for s in _SENT.split(text) if s.strip()]


def chunk_text(text: str, max_chars: int = 400) -> list[str]:
    """Group sentences into chunks of up to ~max_chars so each chunk is a coherent idea."""
    chunks: list[str] = []
    buf = ""
    for sent in split_sentences(text):
        if buf and len(buf) + 1 + len(sent) > max_chars:
            chunks.append(buf)
            buf = sent
        else:
            buf = f"{buf} {sent}".strip()
    if buf:
        chunks.append(buf)
    return chunks
