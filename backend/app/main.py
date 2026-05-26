"""Omnisense Phase-0 API.

Privacy by construction: the server records nothing on its own — memory is created only by
an explicit /ingest call (default-off capture). /data wipes everything for the caller
(one-tap delete). Run: `uvicorn app.main:app --reload` (offline mock providers by default).

Multi-tenancy (Phase-0 skeleton): the caller's identity is passed in the `X-User-Id`
header. Missing → "default" (so the offline demo + tests keep working). This is NOT real
auth — it is a placeholder for the eventual Telegram-OAuth + Payme/Click flow. But it
enforces tenant isolation at the store level today, so the demo can be shared with two
investors without their memories bleeding into each other.
"""
from __future__ import annotations

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from . import __version__
from .pipeline import DEFAULT_TENANT, ConsentRequired, Pipeline
from .schemas import AskRequest, AskResponse, IngestResponse, IngestTextRequest

app = FastAPI(title="Omnisense", version=__version__,
              description="Personal-memory AI — Phase 0 thin loop (Uzbek/Russian).")

# Open CORS for the local web demo / mobile client during development.
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

pipeline = Pipeline()


@app.exception_handler(ConsentRequired)
async def _consent_handler(request, exc: ConsentRequired):
    """Cross-border provider configured but tenant has not consented. 451 = Unavailable
    For Legal Reasons — the right code for "we'd serve you, but the law says we can't
    until you tell us we can." (RFC 7725.)"""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=451,
        content={
            "error": "consent_required",
            "scope": exc.scope,
            "provider": exc.provider,
            "detail": (
                f"This call would use the cross-border provider {exc.provider!r}. "
                f"Grant scope {exc.scope!r} first: POST /consent/{exc.scope} "
                f"with body {{'granted': true}}."
            ),
        },
    )


class ConsentBody(BaseModel):
    granted: bool
    reason: str | None = None


def _tenant(x_user_id: str | None) -> str:
    """Coerce the X-User-Id header into a tenant_id. Empty / missing → "default".

    Light validation only — real auth (Telegram OAuth, signed JWT, ...) is post-Phase-0.
    """
    if not x_user_id:
        return DEFAULT_TENANT
    tid = x_user_id.strip()
    if not tid or len(tid) > 128:
        raise HTTPException(status_code=400, detail="X-User-Id must be 1..128 chars")
    return tid


@app.get("/health")
def health(x_user_id: str | None = Header(default=None)) -> dict:
    tid = _tenant(x_user_id)
    return {"status": "ok", "version": __version__, "tenant": tid, **pipeline.stats(tid)}


@app.post("/ingest/text", response_model=IngestResponse)
def ingest_text(req: IngestTextRequest,
                x_user_id: str | None = Header(default=None)) -> IngestResponse:
    tid = _tenant(x_user_id)
    session = pipeline.ingest_text(req.text, req.lang, req.source, req.speaker, tenant_id=tid)
    return IngestResponse(
        session_id=session.id,
        segments=len([s for s in pipeline.store.all_segments(tid) if s.session_id == session.id]),
    )


@app.post("/ingest/audio", response_model=IngestResponse)
async def ingest_audio(file: UploadFile = File(...),
                       lang: str = Form("ru"),
                       source: str = Form("upload"),
                       x_user_id: str | None = Header(default=None)) -> IngestResponse:
    tid = _tenant(x_user_id)
    audio = await file.read()
    session = pipeline.ingest_audio(audio, lang, source, tenant_id=tid)
    return IngestResponse(
        session_id=session.id,
        segments=len([s for s in pipeline.store.all_segments(tid) if s.session_id == session.id]),
    )


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, x_user_id: str | None = Header(default=None)) -> AskResponse:
    tid = _tenant(x_user_id)
    return AskResponse(**pipeline.ask(
        req.question, req.lang,
        tenant_id=tid, session_id=req.session_id, since=req.since, until=req.until,
    ))


@app.get("/briefing")
def briefing(lang: str | None = None,
             x_user_id: str | None = Header(default=None)) -> dict:
    return pipeline.briefing(lang, tenant_id=_tenant(x_user_id))


@app.get("/sessions")
def sessions(x_user_id: str | None = Header(default=None)) -> dict:
    tid = _tenant(x_user_id)
    return {"sessions": [s.__dict__ for s in pipeline.store.list_sessions(tid)]}


@app.delete("/data")
def delete_all(x_user_id: str | None = Header(default=None)) -> dict:
    return {"deleted_segments": pipeline.delete_all(_tenant(x_user_id))}


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str,
                   x_user_id: str | None = Header(default=None)) -> dict:
    """Forget one meeting. Returns count of removed segments (0 if unknown id)."""
    return {
        "deleted_segments": pipeline.delete_session(session_id, _tenant(x_user_id)),
        "session_id": session_id,
    }


@app.get("/usage")
def usage(x_user_id: str | None = Header(default=None)) -> dict:
    """Per-tenant counters (segments / questions / briefings / last_active_at). The
    skeleton for the billing + quota story — see app/usage.py."""
    return pipeline.usage.get(_tenant(x_user_id))


# ---- consent + region gating -------------------------------------------------
@app.get("/consent")
def consent_status(x_user_id: str | None = Header(default=None)) -> dict:
    """Current consent state per scope + the full append-only audit log.
    Used by the mobile Settings screen and by anyone exercising rights under
    Personal-Data Law ZRU-547."""
    return pipeline.consent(_tenant(x_user_id)).status()


@app.post("/consent/{scope}")
def consent_record(scope: str, body: ConsentBody,
                   x_user_id: str | None = Header(default=None)) -> dict:
    """Append a grant or revoke to the consent log. Latest entry wins; older
    entries are NEVER deleted (audit trail).

    Known scopes: "recording", "cross_border_llm", "cross_border_stt",
    "background_capture". Unknown scopes are accepted (forward-compatible) but
    have no enforcement attached."""
    return pipeline.consent(_tenant(x_user_id)).record(scope, body.granted, body.reason)


# ---- owner-voice enrollment --------------------------------------------------
# Voiceprint stays local (residency-compliant). The reference clip is consumed to compute
# the embedding and then dropped — we never store raw enrollment audio.
@app.get("/enroll/owner")
def enroll_status(x_user_id: str | None = Header(default=None)) -> dict:
    return pipeline.owner(_tenant(x_user_id)).status()


@app.post("/enroll/owner")
async def enroll_owner(file: UploadFile = File(...),
                       x_user_id: str | None = Header(default=None)) -> dict:
    if pipeline.diarizer is None:
        raise HTTPException(
            status_code=400,
            detail="Owner enrollment requires a diarizer. Set OMNI_DIARIZER=mock|pyannote.",
        )
    audio = await file.read()
    voiceprint = pipeline.diarizer.embed_voice(audio)
    if not voiceprint:
        raise HTTPException(status_code=400, detail="Could not embed the reference clip.")
    return pipeline.owner(_tenant(x_user_id)).enroll([voiceprint])


@app.delete("/enroll/owner")
def enroll_clear(x_user_id: str | None = Header(default=None)) -> dict:
    pipeline.owner(_tenant(x_user_id)).clear()
    return {"enrolled": False}
