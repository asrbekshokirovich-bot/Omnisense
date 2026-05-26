"""Word + character error rate — the core metrics for the Uzbek/Russian transcription
risk check.

Both are computed via Levenshtein edit distance:
  WER = edit_distance(ref_words, hyp_words) / len(ref_words)
  CER = edit_distance(ref_chars, hyp_chars) / len(ref_chars)

CER is useful for Uzbek specifically: Latin/Cyrillic mixing and morphology mean a
small character-level difference often becomes a full-word WER hit (e.g. "kelishdik"
vs "kelishtik" = 1 WER but ~10% CER) — comparing both protects against models that
are tokenization-clever but phonetically wrong.

Pure stdlib.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Sequence

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)


def normalize_words(text: str) -> list[str]:
    text = unicodedata.normalize("NFKC", text).lower()
    text = _PUNCT.sub(" ", text)
    return text.split()


def normalize_chars(text: str) -> list[str]:
    text = unicodedata.normalize("NFKC", text).lower()
    text = _PUNCT.sub("", text)
    return [c for c in text if not c.isspace()]


def edit_distance(ref: Sequence, hyp: Sequence) -> int:
    if not ref:
        return len(hyp)
    if not hyp:
        return len(ref)
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, 1):
            cost = 0 if r == h else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[len(hyp)]


def wer(reference: str, hypothesis: str) -> float:
    ref, hyp = normalize_words(reference), normalize_words(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    return edit_distance(ref, hyp) / len(ref)


def cer(reference: str, hypothesis: str) -> float:
    ref, hyp = normalize_chars(reference), normalize_chars(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    return edit_distance(ref, hyp) / len(ref)
