"""The thin loop: ingest -> transcribe -> diarize -> chunk -> embed -> store -> ask / brief.

Providers and the store are injected, so the same pipeline runs offline (mock + in-memory)
for the demo and in production (Yandex/self-hosted STT + pgvector) by changing env only.
"""
from __future__ import annotations

from .chunking import chunk_text
from .config import Settings, settings
from .domain import Segment, Session
from .owner import OwnerEnrollment
from .providers import make_diarizer, make_embedding, make_llm, make_stt
from .store import make_store


class Pipeline:
    def __init__(self, s: Settings = settings) -> None:
        self.settings = s
        self.stt = make_stt(s)
        self.embed = make_embedding(s)
        self.llm = make_llm(s)
        self.store = make_store(s, dim=self.embed.dim)
        self.diarizer = make_diarizer(s)
        self.owner = OwnerEnrollment(
            path=s.owner_voiceprint_path or None,
            threshold=s.owner_match_threshold,
        )

    # ---- ingest -------------------------------------------------------------
    def ingest_audio(self, audio: bytes, lang: str, source: str = "upload") -> Session:
        stt_segments = self.stt.transcribe(audio, lang)
        if self.diarizer is not None and stt_segments:
            stt_segments = self._relabel_with_diarizer(stt_segments, audio)
        return self._store_segments(stt_segments, lang, source)

    def _relabel_with_diarizer(self, stt_segments: list[dict], audio: bytes) -> list[dict]:
        """Replace each STT segment's speaker with the diarizer's label for the same time
        window; map diarizer labels to "owner" when an enrolled voiceprint matches.

        STT (e.g. Yandex short-audio) often returns no diarization at all, so we trust
        the diarizer's own turn boundaries when STT has none. When STT does have its own
        timing, we attribute each STT segment to the diarizer turn it overlaps most.
        """
        turns = self.diarizer.diarize(audio)
        if not turns:
            return stt_segments

        # Decide "owner" label per diarizer speaker_label, using the average voiceprint.
        label_to_voiceprints: dict[str, list[list[float]]] = {}
        for t in turns:
            label_to_voiceprints.setdefault(t["speaker_label"], []).append(t["voiceprint"])
        label_name: dict[str, str] = {}
        owner_seen = False
        other_idx = 0
        for label, vecs in label_to_voiceprints.items():
            centroid = [sum(col) / len(vecs) for col in zip(*vecs)] if vecs else []
            if self.owner.is_owner(centroid) and not owner_seen:
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

    def ingest_text(self, text: str, lang: str, source: str = "text", speaker: str = "owner") -> Session:
        # Pre-transcribed text path (used by the web demo and tests).
        stt_like = []
        t = 0
        for chunk in chunk_text(text):
            stt_like.append({"text": chunk, "start_ms": t, "end_ms": t + 6000, "speaker": speaker})
            t += 6000
        return self._store_segments(stt_like, lang, source)

    def _store_segments(self, stt_segments: list[dict], lang: str, source: str) -> Session:
        session = Session(source=source, lang=lang)
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
                ))
        if segments:
            vectors = self.embed.embed([s.text for s in segments])
            for seg, vec in zip(segments, vectors):
                seg.embedding = vec
        self.store.add_session(session)
        self.store.add_segments(segments)
        return session

    # ---- recall -------------------------------------------------------------
    def ask(self, question: str, lang: str | None = None) -> dict:
        lang = lang or self.settings.default_lang
        query_vec = self.embed.embed([question])[0]
        hits = self.store.search(query_vec, self.settings.retrieval_top_k)
        context = [{**seg.citation(), "score": round(score, 4)} for seg, score in hits]
        answer = self.llm.answer(question, context, lang)
        return {"question": question, "answer": answer, "citations": context}

    def briefing(self, lang: str | None = None) -> dict:
        lang = lang or self.settings.default_lang
        segments = [s.citation() for s in self.store.all_segments()]
        result = self.llm.summarize_day(segments, lang)
        result["segments_count"] = len(segments)
        return result

    # ---- privacy ------------------------------------------------------------
    def delete_all(self) -> int:
        return self.store.delete_all()

    def stats(self) -> dict:
        return {
            "sessions": len(self.store.list_sessions()),
            "segments": len(self.store.all_segments()),
            "providers": {
                "stt": self.settings.stt_provider,
                "embed": self.settings.embed_provider,
                "llm": self.settings.llm_provider,
                "store": self.settings.store_backend,
            },
        }
