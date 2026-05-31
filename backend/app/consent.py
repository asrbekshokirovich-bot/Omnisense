"""Per-tenant consent log: an append-only record of what each tenant has authorized,
when, and why (or revoked).

This is the load-bearing artifact for Uzbekistan's Personal-Data Law No. ZRU-547: if a
regulator asks "who consented to what, and when?" the answer is this log. It also
powers the region gate that refuses to call a cross-border LLM unless the relevant
consent is on file (see Pipeline._require_consent in app/pipeline.py).

Scopes used by Phase 0:

  - "recording"          — the app may capture audio at all.
  - "cross_border_llm"   — derived TEXT may be sent abroad to an LLM for answers
                           and briefings. Voice/voiceprints NEVER cross.
  - "cross_border_stt"   — audio may be sent abroad for STT. Optional; the in-country
                           self-hosted Whisper (docs/development-plan.md §6) is the
                           production path that does NOT require this.
  - "background_capture" — Phase-1 background recording.

Persistence is one JSON file per tenant (path is per-tenant the same way owner
voiceprints are; empty base path = in-memory only). The log is append-only — revoking
adds a new entry rather than deleting the original grant, so the audit trail survives.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class ConsentEntry:
    scope: str
    granted: bool
    at: float = field(default_factory=time.time)
    reason: str | None = None


class ConsentLog:
    def __init__(self, path: str | None = None) -> None:
        self._path = Path(path) if path else None
        self._entries: list[ConsentEntry] = []
        self._load()

    # ---- mutation -----------------------------------------------------------
    def record(self, scope: str, granted: bool, reason: str | None = None) -> dict:
        if not scope or not isinstance(scope, str):
            raise ValueError("scope must be a non-empty string")
        entry = ConsentEntry(scope=scope.strip(), granted=bool(granted), reason=reason)
        self._entries.append(entry)
        self._save()
        return asdict(entry)

    # ---- query --------------------------------------------------------------
    def is_granted(self, scope: str) -> bool:
        """Latest entry wins. Missing scope → not granted (fail-closed)."""
        for e in reversed(self._entries):
            if e.scope == scope:
                return e.granted
        return False

    def status(self) -> dict:
        """Current state per scope + the full log (audit trail)."""
        latest: dict[str, ConsentEntry] = {}
        for e in self._entries:
            latest[e.scope] = e  # last write wins
        return {
            "current": {k: asdict(v) for k, v in latest.items()},
            "log": [asdict(e) for e in self._entries],
        }

    # ---- persistence --------------------------------------------------------
    def _load(self) -> None:
        if not self._path or not self._path.is_file():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._entries = [
                ConsentEntry(scope=r["scope"], granted=bool(r["granted"]),
                             at=float(r.get("at", time.time())),
                             reason=r.get("reason"))
                for r in data
            ]
        except (json.JSONDecodeError, ValueError, OSError, KeyError):
            # Corrupt file → start fresh. Re-grants overwrite via append.
            self._entries = []

    def _save(self) -> None:
        if not self._path:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([asdict(e) for e in self._entries]),
            encoding="utf-8",
        )
