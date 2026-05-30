"""The thin loop: ingest -> transcribe -> diarize -> chunk -> embed -> store -> ask / brief.

Multi-tenant from task 5 onward — every public method takes a `tenant_id`. Stores are
shared across tenants but filter on tenant_id; owner enrollment and usage counters are
per-tenant.

Providers and the store are injected, so the same pipeline runs offline (mock + in-memory)
for the demo and in production (Yandex/self-hosted STT + pgvector) by changing env only.
"""
from __future__ import annotations

from pathlib import Path

from .auth import ApiKeyStore
from .billing import SubscriptionStore, make_billing
from .chunking import chunk_text
from .config import Settings, settings
from .consent import ConsentLog
from .domain import Segment, Session
from .encryption import make_encryptor
from .owner import OwnerEnrollment
from .providers import make_diarizer, make_embedding, make_llm, make_stt
from .ratelimit import TokenBucketLimiter
from .store import make_store
from .usage import UsageMeter

DEFAULT_TENANT = "default"

# Cross-border-LLM providers — these need explicit "cross_border_llm" consent before
# Pipeline.ask / briefing will invoke them. "mock" stays in-process so it is free.
_CROSS_BORDER_LLMS = {"anthropic", "openai"}
_CROSS_BORDER_STT = {"yandex"}


class ConsentRequired(PermissionError):
    """Raised when a cross-border provider is configured but the tenant has not granted
    the matching consent scope. The API layer turns this into a 451 (Unavailable For
    Legal Reasons)."""

    def __init__(self, scope: str, provider: str) -> None:
        super().__init__(f"consent scope {scope!r} required for provider {provider!r}")
        self.scope = scope
        self.provider = provider


class Pipeline:
    def __init__(self, s: Settings = settings) -> None:
        self.settings = s
        self.stt = make_stt(s)
        self.embed = make_embedding(s)
        self.llm = make_llm(s)
        self.store = make_store(s, dim=self.embed.dim)
        self.diarizer = make_diarizer(s)
        self.usage = UsageMeter()
        self.subscriptions = SubscriptionStore()
        self.billing = make_billing(s)
        self.api_keys = ApiKeyStore()
        self.rate_limiter = TokenBucketLimiter(
            rate_per_min=s.rate_per_min, burst=s.rate_burst,
        )
        self.encryptor = make_encryptor(s.encryption, s.kek_b64)
        # One OwnerEnrollment + one ConsentLog per tenant — cached lazily.
        self._owners: dict[str, OwnerEnrollment] = {}
        self._consent: dict[str, ConsentLog] = {}

    # ---- per-tenant owner-enrollment ----------------------------------------
    def owner(self, tenant_id: str = DEFAULT_TENANT) -> OwnerEnrollment:
        e = self._owners.get(tenant_id)
        if e is None:
            e = OwnerEnrollment(
                path=self._owner_path(tenant_id),
                threshold=self.settings.owner_match_threshold,
            )
            self._owners[tenant_id] = e
        return e

    def _owner_path(self, tenant_id: str) -> str | None:
        """Per-tenant persistence path: `<base>.<tenant>.json`. Empty base → in-memory."""
        base = self.settings.owner_voiceprint_path
        if not base:
            return None
        p = Path(base)
        # Insert tenant id before the suffix so all tenants live alongside each other but
        # cannot collide. Plain filename ("owner.json") → "owner.default.json".
        return str(p.with_name(f"{p.stem}.{tenant_id}{p.suffix or '.json'}"))

    # ---- per-tenant consent log ---------------------------------------------
    def consent(self, tenant_id: str = DEFAULT_TENANT) -> ConsentLog:
        c = self._consent.get(tenant_id)
        if c is None:
            c = ConsentLog(path=self._consent_path(tenant_id))
            self._consent[tenant_id] = c
        return c

    def _consent_path(self, tenant_id: str) -> str | None:
        base = self.settings.consent_log_path
        if not base:
            return None
        p = Path(base)
        return str(p.with_name(f"{p.stem}.{tenant_id}{p.suffix or '.json'}"))

    # ---- region gate --------------------------------------------------------
    def _require_consent_for_llm(self, tenant_id: str) -> None:
        if self.settings.llm_provider in _CROSS_BORDER_LLMS:
            if not self.consent(tenant_id).is_granted("cross_border_llm"):
                raise ConsentRequired("cross_border_llm", self.settings.llm_provider)

    def _require_consent_for_stt(self, tenant_id: str) -> None:
        if self.settings.stt_provider in _CROSS_BORDER_STT:
            if not self.consent(tenant_id).is_granted("cross_border_stt"):
                raise ConsentRequired("cross_border_stt", self.settings.stt_provider)

    # ---- ingest -------------------------------------------------------------
    def ingest_audio(self, audio: bytes, lang: str, source: str = "upload",
                     tenant_id: str = DEFAULT_TENANT) -> Session:
        self._require_consent_for_stt(tenant_id)
        stt_segments = self.stt.transcribe(audio, lang)
        if self.diarizer is not None and stt_segments:
            stt_segments = self._relabel_with_diarizer(stt_segments, audio, tenant_id)
        return self._store_segments(stt_segments, lang, source, tenant_id)

    def ingest_text(self, text: str, lang: str, source: str = "text",
                    speaker: str = "owner", tenant_id: str = DEFAULT_TENANT) -> Session:
        # Pre-transcribed text path (used by the web demo and tests).
        stt_like = []
        t = 0
        for chunk in chunk_text(text):
            stt_like.append({"text": chunk, "start_ms": t, "end_ms": t + 6000, "speaker": speaker})
            t += 6000
        return self._store_segments(stt_like, lang, source, tenant_id)

    def _relabel_with_diarizer(self, stt_segments: list[dict], audio: bytes,
                               tenant_id: str) -> list[dict]:
        """Replace each STT segment's speaker with the diarizer's label for the same time
        window; map diarizer labels to "owner" when this tenant's enrolled voiceprint
        matches.
        """
        turns = self.diarizer.diarize(audio)
        if not turns:
            return stt_segments

        # Decide "owner" label per diarizer speaker_label, using the average voiceprint.
        owner = self.owner(tenant_id)
        label_to_voiceprints: dict[str, list[list[float]]] = {}
        for t in turns:
            label_to_voiceprints.setdefault(t["speaker_label"], []).append(t["voiceprint"])
        label_name: dict[str, str] = {}
        owner_seen = False
        other_idx = 0
        for label, vecs in label_to_voiceprints.items():
            centroid = [sum(col) / len(vecs) for col in zip(*vecs)] if vecs else []
            if owner.is_owner(centroid) and not owner_seen:
                label_name[label] = "owner"
                owner_seen = True
            else:
                label_name[label] = f"other_{other_idx}" if other_idx else "other"
                other_idx += 1

        def overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> int:
            return max(0, min(a_end, b_end) - max(a_start, b_start))

        out: list[dict] = []
        for seg in stt_segments:
            seg_start = int(seg.get("start_ms", 0))
            seg_end = int(seg.get("end_ms", seg_start + 6000))
            best = max(
                turns,
                key=lambda t: overlap(seg_start, seg_end, t["start_ms"], t["end_ms"]),
                default=None,
            )
            new = dict(seg)
            if best is not None and overlap(seg_start, seg_end, best["start_ms"], best["end_ms"]) > 0:
                new["speaker"] = label_name[best["speaker_label"]]
            out.append(new)
        return out

    def _store_segments(self, stt_segments: list[dict], lang: str, source: str,
                        tenant_id: str) -> Session:
        session = Session(source=source, lang=lang, tenant_id=tenant_id)
        segments: list[Segment] = []
        for raw in stt_segments:
            for chunk in chunk_text(raw["text"]) or [raw["text"]]:
                segments.append(Segment(
                    text=chunk,
                    session_id=session.id,
                    speaker=raw.get("speaker", "unknown"),
                    start_ms=raw.get("start_ms", 0),
                    end_ms=raw.get("end_ms", 0),
                    lang=lang,
                    tenant_id=tenant_id,
                ))
        if segments:
            # Embed plaintext first — the embedder needs to see real text. Encryption
            # happens just before the segment lands in the store, so the embeddings
            # (computed in-country) and the at-rest ciphertext are both correct.
            vectors = self.embed.embed([s.text for s in segments])
            for seg, vec in zip(segments, vectors):
                seg.embedding = vec
                seg.text = self.encryptor.encrypt(seg.text, tenant_id)
        self.store.add_session(session)
        self.store.add_segments(segments)
        self.usage.record_ingest(tenant_id, len(segments))
        return session

    def _decrypt_segment(self, seg: Segment) -> Segment:
        """Return a copy of `seg` with text decrypted. Original is left intact (so
        callers that need the at-rest form still see it)."""
        from dataclasses import replace
        return replace(seg, text=self.encryptor.decrypt(seg.text, seg.tenant_id))

    # ---- recall -------------------------------------------------------------
    def ask(
        self,
        question: str,
        lang: str | None = None,
        *,
        tenant_id: str = DEFAULT_TENANT,
        session_id: str | None = None,
        since: float | None = None,
        until: float | None = None,
    ) -> dict:
        self._require_consent_for_llm(tenant_id)
        lang = lang or self.settings.default_lang
        query_vec = self.embed.embed([question])[0]
        # `lang` controls the LLM reply language; we do NOT use it as a recall filter,
        # since RU questions over UZ memories (and vice versa) are common in Tashkent.
        hits = self.store.search(
            query_vec, self.settings.retrieval_top_k,
            tenant_id=tenant_id,
            session_id=session_id, since=since, until=until,
        )
        context = [
            {**self._decrypt_segment(seg).citation(), "score": round(score, 4)}
            for seg, score in hits
        ]
        answer = self.llm.answer(question, context, lang)
        self.usage.record_question(tenant_id)
        return {"question": question, "answer": answer, "citations": context}

    def briefing(self, lang: str | None = None, *, tenant_id: str = DEFAULT_TENANT) -> dict:
        self._require_consent_for_llm(tenant_id)
        lang = lang or self.settings.default_lang
        segments = [
            self._decrypt_segment(s).citation()
            for s in self.store.all_segments(tenant_id)
        ]
        result = self.llm.summarize_day(segments, lang)
        result["segments_count"] = len(segments)
        self.usage.record_briefing(tenant_id)
        return result

    # ---- privacy ------------------------------------------------------------
    def delete_all(self, tenant_id: str = DEFAULT_TENANT) -> int:
        self.usage.reset(tenant_id)
        return self.store.delete_all(tenant_id)

    def delete_session(self, session_id: str, tenant_id: str = DEFAULT_TENANT) -> int:
        return self.store.delete_session(session_id, tenant_id)

    def stats(self, tenant_id: str = DEFAULT_TENANT) -> dict:
        return {
            "sessions": len(self.store.list_sessions(tenant_id)),
            "segments": len(self.store.all_segments(tenant_id)),
            "providers": {
                "stt": self.settings.stt_provider,
                "embed": self.settings.embed_provider,
                "llm": self.settings.llm_provider,
                "store": self.settings.store_backend,
                "diarizer": self.settings.diarizer_provider,
            },
        }
