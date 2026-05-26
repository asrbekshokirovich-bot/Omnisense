"""The thin loop: ingest -> transcribe -> chunk -> embed -> store -> ask / brief.

Providers and the store are injected, so the same pipeline runs offline (mock + in-memory)
for the demo and in production (Yandex/self-hosted STT + pgvector) by changing env only.
"""
from __future__ import annotations

from .chunking import chunk_text
from .config import Settings, settings
from .domain import Segment, Session
from .providers import make_embedding, make_llm, make_stt
from .store import make_store


class Pipeline:
    def __init__(self, s: Settings = settings) -> None:
        self.settings = s
        self.stt = make_stt(s)
        self.embed = make_embedding(s)
        self.llm = make_llm(s)
        self.store = make_store(s)

    # ---- ingest -------------------------------------------------------------
    def ingest_audio(self, audio: bytes, lang: str, source: str = "upload") -> Session:
        stt_segments = self.stt.transcribe(audio, lang)
        return self._store_segments(stt_segments, lang, source)

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
