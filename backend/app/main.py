"""Omnisense Phase-0 API.

Privacy by construction: the server records nothing on its own — memory is created only by
an explicit /ingest call (default-off capture). /data wipes everything (one-tap delete).
Run: `uvicorn app.main:app --reload` (offline mock providers by default).
"""
from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .pipeline import Pipeline
from .schemas import AskRequest, AskResponse, IngestResponse, IngestTextRequest

app = FastAPI(title="Omnisense", version=__version__,
              description="Personal-memory AI — Phase 0 thin loop (Uzbek/Russian).")

# Open CORS for the local web demo / mobile client during development.
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

pipeline = Pipeline()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__, **pipeline.stats()}


@app.post("/ingest/text", response_model=IngestResponse)
def ingest_text(req: IngestTextRequest) -> IngestResponse:
    session = pipeline.ingest_text(req.text, req.lang, req.source, req.speaker)
    return IngestResponse(session_id=session.id,
                          segments=len([s for s in pipeline.store.all_segments()
                                        if s.session_id == session.id]))


@app.post("/ingest/audio", response_model=IngestResponse)
async def ingest_audio(file: UploadFile = File(...),
                       lang: str = Form("ru"),
                       source: str = Form("upload")) -> IngestResponse:
    audio = await file.read()
    session = pipeline.ingest_audio(audio, lang, source)
    return IngestResponse(session_id=session.id,
                          segments=len([s for s in pipeline.store.all_segments()
                                        if s.session_id == session.id]))


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    return AskResponse(**pipeline.ask(req.question, req.lang))


@app.get("/briefing")
def briefing(lang: str | None = None) -> dict:
    return pipeline.briefing(lang)


@app.get("/sessions")
def sessions() -> dict:
    return {"sessions": [s.__dict__ for s in pipeline.store.list_sessions()]}


@app.delete("/data")
def delete_all() -> dict:
    return {"deleted_segments": pipeline.delete_all()}


# ---- owner-voice enrollment --------------------------------------------------
# Voiceprint stays local (residency-compliant). The reference clip is consumed to compute
# the embedding and then dropped — we never store raw enrollment audio.
@app.get("/enroll/owner")
def enroll_status() -> dict:
    return pipeline.owner.status()


@app.post("/enroll/owner")
async def enroll_owner(file: UploadFile = File(...)) -> dict:
    if pipeline.diarizer is None:
        raise HTTPException(
            status_code=400,
            detail="Owner enrollment requires a diarizer. Set OMNI_DIARIZER=mock|pyannote.",
        )
    audio = await file.read()
    voiceprint = pipeline.diarizer.embed_voice(audio)
    if not voiceprint:
        raise HTTPException(status_code=400, detail="Could not embed the reference clip.")
    return pipeline.owner.enroll([voiceprint])


@app.delete("/enroll/owner")
def enroll_clear() -> dict:
    pipeline.owner.clear()
    return {"enrolled": False}
