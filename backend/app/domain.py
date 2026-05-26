"""Core data types for the memory loop. Pure stdlib so the logic is testable without infra."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


def _id() -> str:
    return uuid.uuid4().hex


@dataclass
class Segment:
    """A short, timestamped, speaker-attributed piece of a transcript — the unit of memory."""
    text: str
    session_id: str = ""
    speaker: str = "unknown"
    start_ms: int = 0
    end_ms: int = 0
    lang: str = "ru"
    id: str = field(default_factory=_id)
    created_at: float = field(default_factory=time.time)
    embedding: list[float] = field(default_factory=list)

    def citation(self) -> dict:
        """A compact reference returned alongside answers."""
        return {
            "session_id": self.session_id,
            "speaker": self.speaker,
            "start_ms": self.start_ms,
            "timestamp": _fmt_ts(self.start_ms),
            "text": self.text,
        }


@dataclass
class Session:
    """One capture (a meeting, a conversation)."""
    source: str = "demo"
    lang: str = "ru"
    id: str = field(default_factory=_id)
    created_at: float = field(default_factory=time.time)


def _fmt_ts(ms: int) -> str:
    s = ms // 1000
    return f"{s // 60:02d}:{s % 60:02d}"
