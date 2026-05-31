"""Owner-voice enrollment: a single centroid voiceprint + a cosine-threshold match.

What this is: the device owner uploads one (or more) short reference clips of themselves
speaking. We embed each clip through the configured Diarizer's voiceprint model, average
the embeddings into a centroid, and persist it. Later, when a meeting is diarized, we
compare each discovered speaker's voiceprint to the centroid; if cosine ≥ threshold we
re-label that speaker as "owner" (and the others as "other_N").

What this is not: speaker identification of arbitrary people. Just a 1-vs-many "is this
the owner?" check — that is the minimum needed to power "what did *I* commit to?" briefs
without leaking voice biometrics to third parties.

Persistence: a single JSON file (path from settings). Empty path = in-memory only (tests).
The file is intentionally small + portable so it can be wiped by `DELETE /enroll/owner`
and re-uploaded — matching the one-tap-delete privacy guarantee.

Residency: voiceprints never leave the box. They are never sent to the cross-border LLM.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def _mean(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    dim = len(vectors[0])
    out = [0.0] * dim
    for v in vectors:
        for i, x in enumerate(v):
            out[i] += x
    return [x / len(vectors) for x in out]


class OwnerEnrollment:
    """Centroid + threshold + optional persistence to a JSON file."""

    def __init__(self, path: str | None = None, threshold: float = 0.7) -> None:
        self._path = Path(path) if path else None
        self.threshold = threshold
        self.centroid: list[float] = []
        self.sample_count: int = 0
        self._load()

    # -- state ----------------------------------------------------------------
    @property
    def enrolled(self) -> bool:
        return bool(self.centroid)

    def status(self) -> dict:
        return {
            "enrolled": self.enrolled,
            "samples": self.sample_count,
            "threshold": self.threshold,
            "voiceprint_dim": len(self.centroid),
        }

    # -- mutation -------------------------------------------------------------
    def enroll(self, voiceprints: Iterable[list[float]]) -> dict:
        """Replace the centroid with the mean of the given voiceprints."""
        vectors = [list(v) for v in voiceprints if v]
        if not vectors:
            raise ValueError("enroll() requires at least one non-empty voiceprint")
        self.centroid = _mean(vectors)
        self.sample_count = len(vectors)
        self._save()
        return self.status()

    def clear(self) -> None:
        self.centroid = []
        self.sample_count = 0
        if self._path and self._path.is_file():
            self._path.unlink()

    # -- query ----------------------------------------------------------------
    def is_owner(self, voiceprint: list[float]) -> bool:
        if not self.enrolled or not voiceprint:
            return False
        return _cosine(self.centroid, voiceprint) >= self.threshold

    def score(self, voiceprint: list[float]) -> float:
        if not self.enrolled or not voiceprint:
            return 0.0
        return _cosine(self.centroid, voiceprint)

    # -- persistence ----------------------------------------------------------
    def _load(self) -> None:
        if not self._path or not self._path.is_file():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self.centroid = list(data.get("centroid", []))
            self.sample_count = int(data.get("samples", 0))
            self.threshold = float(data.get("threshold", self.threshold))
        except (json.JSONDecodeError, ValueError, OSError):
            # Corrupt or unreadable — treat as not enrolled. Re-enrolling overwrites.
            self.centroid = []
            self.sample_count = 0

    def _save(self) -> None:
        if not self._path:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps({
                "centroid": self.centroid,
                "samples": self.sample_count,
                "threshold": self.threshold,
            }),
            encoding="utf-8",
        )
