"""Knowledge-graph memory — entities, relations, temporal markers extracted from
conversation. Sits **alongside** the vector store, never replaces it.

Why both? Vector search nails "find a passage that sounds like this question". A KG
nails "what did Asal commit to last week" and "show me everyone we promised something
to" — queries that are about *structured entities and time*, not topical similarity.
The two paths feed one /ask in Phase 1; today the KG is exposed at /facts so the team
can see it land alongside the vector recall.

Phase-0 ships the *shape*:
  - `KnowledgeGraph` interface — extract_facts, search_facts, list/delete, tenant
    scoping mandatory on every read.
  - `MockKnowledgeGraph` — rule-based, in-memory, zero deps. Catches the meeting
    patterns we actually demo on: action items ("I will…"), decisions
    ("we agreed…"), and three-language temporal hints (RU/UZ/EN).
  - `GraphitiKnowledgeGraph` + `Mem0KnowledgeGraph` — STUBS. They raise on
    construction so a misconfigured OMNI_KG=graphiti deploy fails loud rather than
    silently no-op'ing. Real adapters land with the Neo4j (Graphiti) /
    Mem0-cloud-or-self-hosted decisions the team has yet to make. The interface
    stays fixed so the swap is a config change.

Default: OMNI_KG=off so the offline demo + existing tests stay untouched. Wiring is
purely additive — Pipeline still works without a KG.
"""
from __future__ import annotations

import re
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Fact:
    subject: str
    predicate: str
    object: str
    temporal: str | None = None
    confidence: float = 0.5
    segment_id: str = ""
    session_id: str = ""
    tenant_id: str = "default"
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object,
            "temporal": self.temporal,
            "confidence": self.confidence,
            "segment_id": self.segment_id,
            "session_id": self.session_id,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at,
        }


class KnowledgeGraph(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def extract_facts(
        self, text: str, *, segment_id: str, session_id: str, tenant_id: str,
    ) -> list[Fact]:
        """Extract + store facts from a transcript chunk. Returns what was stored."""

    @abstractmethod
    def search_facts(
        self, query: str, *, tenant_id: str, top_k: int = 5,
    ) -> list[Fact]: ...

    @abstractmethod
    def list_facts(self, *, tenant_id: str) -> list[Fact]: ...

    @abstractmethod
    def delete_all(self, *, tenant_id: str) -> int: ...

    @abstractmethod
    def delete_session(self, session_id: str, *, tenant_id: str) -> int: ...


# ---- MockKnowledgeGraph: rule-based + in-memory -----------------------------
# These triplet patterns cover meeting-style language in EN / RU / UZ. They are
# deliberately small + auditable; the production extractor (Graphiti / Mem0 / a fine-
# tuned LLM) replaces them without changing call sites.
_TOKEN = re.compile(r"\w+", re.UNICODE)

# (predicate label, regex pattern). Capture group 1 = subject (or empty for "owner"),
# group 2 = object (the commitment / decision content).
_PATTERNS: list[tuple[str, re.Pattern]] = [
    # English
    ("will",
     re.compile(r"\b(?P<sub>I|we|you|they|he|she|[A-ZА-Я][\w'-]*)\s+(?:will|'ll)\s+(?P<obj>.+)",
                re.IGNORECASE)),
    ("agreed",
     re.compile(r"\b(?:we|they)\s+agreed\s+(?:to\s+)?(?P<obj>.+)", re.IGNORECASE)),
    ("decided",
     re.compile(r"\b(?:we|they)\s+decided\s+(?:to\s+)?(?P<obj>.+)", re.IGNORECASE)),
    ("needs_to",
     re.compile(r"\b(?P<sub>I|we|you|they|he|she|[A-ZА-Я][\w'-]*)\s+(?:need|needs|have)\s+to\s+(?P<obj>.+)",
                re.IGNORECASE)),
    # Russian — "договорились" (agreed), "решили" (decided), "должен/нужно" (need to)
    ("agreed",
     re.compile(r"\b(?:мы|они)?\s*договорились\s+(?P<obj>.+)", re.IGNORECASE)),
    ("decided",
     re.compile(r"\b(?:мы|они)?\s*решили\s+(?P<obj>.+)", re.IGNORECASE)),
    ("needs_to",
     re.compile(r"\b(?P<sub>я|мы|они|он|она|вы)?\s*(?:должен|должна|нужно|надо)\s+(?P<obj>.+)",
                re.IGNORECASE)),
    # Uzbek is SOV — object comes BEFORE the verb. "Biz X kelishdik" = "we agreed X".
    ("agreed",
     re.compile(r"\b(?:biz\s+)?(?P<obj>.+?)\s+kelishdik\b", re.IGNORECASE)),
    ("decided",
     re.compile(r"\b(?:biz\s+)?(?P<obj>.+?)\s+qaror\s+qildik\b", re.IGNORECASE)),
    ("needs_to",
     re.compile(r"\b(?P<sub>men|biz|siz|ular|u)?\s*(?P<obj>.+?)\s+kerak\b", re.IGNORECASE)),
    # "X qilaman" / "X qilamiz" = "I/we will do X" — common in Uzbek action items.
    # subject is implicit ("owner" = speaker); we just capture the action.
    ("will",
     re.compile(r"\b(?P<obj>.+?)\s+(?:qilaman|qilamiz|yuboraman|tayyorlayman)\b",
                re.IGNORECASE)),
]

# Temporal hints in three languages. Order matters — we tag the FIRST match per text.
_TEMPORAL: list[tuple[str, re.Pattern]] = [
    ("today",      re.compile(r"\btoday\b|\bсегодня\b|\bbugun\b", re.IGNORECASE)),
    ("tomorrow",   re.compile(r"\btomorrow\b|\bзавтра\b|\bertaga\b", re.IGNORECASE)),
    ("yesterday",  re.compile(r"\byesterday\b|\bвчера\b|\bkecha\b", re.IGNORECASE)),
    ("this_week",  re.compile(r"\bthis week\b|\bна этой неделе\b|\bbu hafta\b", re.IGNORECASE)),
    ("next_week",  re.compile(r"\bnext week\b|\bна следующей неделе\b|\bkeyingi hafta\b", re.IGNORECASE)),
    ("friday",     re.compile(r"\bfriday\b|\bпятниц\w*\b|\bjuma\b", re.IGNORECASE)),
    ("monday",     re.compile(r"\bmonday\b|\bпонедельник\b|\bdushanba\b", re.IGNORECASE)),
]


def _temporal_for(text: str) -> str | None:
    for label, rx in _TEMPORAL:
        if rx.search(text):
            return label
    return None


def _trim(s: str, max_chars: int = 140) -> str:
    s = s.strip().rstrip(".!?…").strip()
    return s if len(s) <= max_chars else s[:max_chars].rstrip() + "…"


class MockKnowledgeGraph(KnowledgeGraph):
    name = "mock"

    def __init__(self) -> None:
        self._facts: list[Fact] = []

    def extract_facts(
        self, text: str, *, segment_id: str, session_id: str, tenant_id: str,
    ) -> list[Fact]:
        text = (text or "").strip()
        if not text:
            return []
        temporal = _temporal_for(text)
        out: list[Fact] = []
        seen: set[tuple[str, str, str]] = set()
        for predicate, rx in _PATTERNS:
            for m in rx.finditer(text):
                groups = m.groupdict()
                subject = (groups.get("sub") or "owner").strip().lower()
                obj = _trim(groups["obj"])
                if not obj:
                    continue
                key = (subject, predicate, obj.lower())
                if key in seen:
                    continue
                seen.add(key)
                out.append(Fact(
                    subject=subject, predicate=predicate, object=obj,
                    temporal=temporal, confidence=0.6,
                    segment_id=segment_id, session_id=session_id, tenant_id=tenant_id,
                ))
        self._facts.extend(out)
        return out

    def search_facts(
        self, query: str, *, tenant_id: str, top_k: int = 5,
    ) -> list[Fact]:
        q_tokens = {t.lower() for t in _TOKEN.findall(query or "")}
        if not q_tokens:
            return self.list_facts(tenant_id=tenant_id)[:top_k]
        scored: list[tuple[Fact, int]] = []
        for f in self._facts:
            if f.tenant_id != tenant_id:
                continue
            hay = {t.lower() for t in _TOKEN.findall(
                f"{f.subject} {f.predicate} {f.object} {f.temporal or ''}"
            )}
            score = len(q_tokens & hay)
            if score > 0:
                scored.append((f, score))
        scored.sort(key=lambda p: (-p[1], -p[0].created_at))
        return [f for f, _ in scored[:top_k]]

    def list_facts(self, *, tenant_id: str) -> list[Fact]:
        return [f for f in self._facts if f.tenant_id == tenant_id]

    def delete_all(self, *, tenant_id: str) -> int:
        before = len(self._facts)
        self._facts = [f for f in self._facts if f.tenant_id != tenant_id]
        return before - len(self._facts)

    def delete_session(self, session_id: str, *, tenant_id: str) -> int:
        before = len(self._facts)
        self._facts = [
            f for f in self._facts
            if not (f.session_id == session_id and f.tenant_id == tenant_id)
        ]
        return before - len(self._facts)


# ---- Adapter stubs (Graphiti, Mem0) -----------------------------------------
class GraphitiKnowledgeGraph(KnowledgeGraph):
    """Graphiti backend — STUB.

    Real implementation requires a running Neo4j (Graphiti's only supported store) +
    Graphiti's Python client. Decisions still open: do we host Neo4j in-country
    ourselves or use Neo4j Aura's nearest region? Both have residency implications
    different from pgvector — pin this with the team before wiring."""

    name = "graphiti"

    def __init__(self, *_args, **_kwargs) -> None:
        raise NotImplementedError(
            "Graphiti adapter needs Neo4j + a residency decision. The KnowledgeGraph "
            "interface is fixed; fill the body once the team picks self-hosted vs. Aura."
        )

    # Methods exist only so the class still satisfies the ABC at import time.
    def extract_facts(self, *a, **kw): raise NotImplementedError
    def search_facts(self, *a, **kw): raise NotImplementedError
    def list_facts(self, *a, **kw): raise NotImplementedError
    def delete_all(self, *a, **kw): raise NotImplementedError
    def delete_session(self, *a, **kw): raise NotImplementedError


class Mem0KnowledgeGraph(KnowledgeGraph):
    """Mem0 backend — STUB. See app/providers/billing_*.py for the same pattern."""

    name = "mem0"

    def __init__(self, *_args, **_kwargs) -> None:
        raise NotImplementedError(
            "Mem0 adapter needs the team's call on hosted vs. self-hosted Mem0 (the "
            "hosted version is cross-border by default — would need cross_border_llm "
            "consent). Interface fixed; body fills in once we pick."
        )

    def extract_facts(self, *a, **kw): raise NotImplementedError
    def search_facts(self, *a, **kw): raise NotImplementedError
    def list_facts(self, *a, **kw): raise NotImplementedError
    def delete_all(self, *a, **kw): raise NotImplementedError
    def delete_session(self, *a, **kw): raise NotImplementedError


# ---- factory ---------------------------------------------------------------
def make_kg(provider: str) -> KnowledgeGraph | None:
    """Return the configured KG, or None when KG memory is disabled (default).

    None is the documented "no KG path" — Pipeline checks for it and skips the
    extraction step.
    """
    if provider == "mock":
        return MockKnowledgeGraph()
    if provider == "graphiti":
        return GraphitiKnowledgeGraph()
    if provider == "mem0":
        return Mem0KnowledgeGraph()
    return None
