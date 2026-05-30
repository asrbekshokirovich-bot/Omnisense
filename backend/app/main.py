"""Omnisense Phase-0 API.

Privacy by construction: the server records nothing on its own — memory is created only by
an explicit /ingest call (default-off capture). /data wipes everything for the caller
(one-tap delete). Run: `uvicorn app.main:app --reload` (offline mock providers by default).

Identity (in order of precedence):
  1. **X-API-Key** — the real-client header. Resolves to a tenant via app/auth.py.
  2. **X-User-Id** — Phase-0 dev shortcut (used by demo, mobile, tests). Missing → "default".

Every request carries an **X-Request-Id** (generated if absent) for log correlation.

A per-tenant token-bucket rate limiter (app/ratelimit.py) guards every endpoint that
mutates or reads memory. /health is intentionally open.
"""
from __future__ import annotations

import uuid

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pydantic import BaseModel

from . import __version__
from .pipeline import DEFAULT_TENANT, ConsentRequired, Pipeline
from .schemas import AskRequest, AskResponse, IngestResponse, IngestTextRequest

app = FastAPI(title="Omnisense", version=__version__,
              description="Personal-memory AI — Phase 0 thin loop (Uzbek/Russian).")

# Open CORS for the local web demo / mobile client during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
    expose_headers=["X-Request-Id"],
)

pipeline = Pipeline()


# ---- middleware: request ID propagation -------------------------------------
@app.middleware("http")
async def _request_id_middleware(request: Request, call_next):
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["X-Request-Id"] = rid
    return response


# ---- shared exception handlers ----------------------------------------------
@app.exception_handler(ConsentRequired)
async def _consent_handler(request: Request, exc: ConsentRequired):
    """Cross-border provider configured but tenant has not consented. 451 = Unavailable
    For Legal Reasons (RFC 7725)."""
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
        headers={"X-Request-Id": getattr(request.state, "request_id", "")},
    )


# ---- request bodies ---------------------------------------------------------
class ConsentBody(BaseModel):
    granted: bool
    reason: str | None = None


class SubscribeBody(BaseModel):
    plan: str
    annual: bool = False


class ApiKeyBody(BaseModel):
    label: str | None = None


# ---- identity + rate limiting -----------------------------------------------
def _validate_user_id(x_user_id: str | None) -> str | None:
    if x_user_id is None:
        return None
    tid = x_user_id.strip()
    if not tid:
        return None
    if len(tid) > 128:
        raise HTTPException(status_code=400, detail="X-User-Id must be 1..128 chars")
    return tid


def resolve_tenant(
    x_api_key: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
) -> str:
    """Tenant for the call. X-API-Key wins; falls back to X-User-Id; else 'default'.

    Invalid X-API-Key → 401. Empty / missing keys + missing X-User-Id → 'default' (so the
    offline demo + tests keep working without setting up keys).
    """
    if x_api_key:
        rec = pipeline.api_keys.resolve(x_api_key.strip())
        if rec is None:
            raise HTTPException(status_code=401, detail="Invalid X-API-Key")
        return rec.tenant_id
    return _validate_user_id(x_user_id) or DEFAULT_TENANT


def rate_limit(tenant_id: str = Depends(resolve_tenant)) -> str:
    """Dependency that resolves the tenant AND charges 1 token to its bucket. Returns
    the tenant_id so endpoint code can just `tid: str = Depends(rate_limit)`. Endpoints
    that want a tenant_id without the rate-limit charge depend on `resolve_tenant`
    directly."""
    allowed, retry_after = pipeline.rate_limiter.acquire(tenant_id, cost=1.0)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"rate limit exceeded; retry in {retry_after:.1f}s",
            headers={"Retry-After": str(max(1, int(retry_after) + 1))},
        )
    return tenant_id


# ---- core endpoints ---------------------------------------------------------
@app.get("/health")
def health(tid: str = Depends(resolve_tenant)) -> dict:
    # Intentionally not rate-limited — load balancers + the mobile app probe this freely.
    return {"status": "ok", "version": __version__, "tenant": tid, **pipeline.stats(tid)}


@app.post("/ingest/text", response_model=IngestResponse)
def ingest_text(req: IngestTextRequest, tid: str = Depends(rate_limit)) -> IngestResponse:
    session = pipeline.ingest_text(req.text, req.lang, req.source, req.speaker, tenant_id=tid)
    return IngestResponse(
        session_id=session.id,
        segments=len([s for s in pipeline.store.all_segments(tid) if s.session_id == session.id]),
    )


@app.post("/ingest/audio", response_model=IngestResponse)
async def ingest_audio(file: UploadFile = File(...),
                       lang: str = Form("ru"),
                       source: str = Form("upload"),
                       tid: str = Depends(rate_limit)) -> IngestResponse:
    audio = await file.read()
    session = pipeline.ingest_audio(audio, lang, source, tenant_id=tid)
    return IngestResponse(
        session_id=session.id,
        segments=len([s for s in pipeline.store.all_segments(tid) if s.session_id == session.id]),
    )


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, tid: str = Depends(rate_limit)) -> AskResponse:
    return AskResponse(**pipeline.ask(
        req.question, req.lang,
        tenant_id=tid, session_id=req.session_id, since=req.since, until=req.until,
    ))


@app.get("/briefing")
def briefing(lang: str | None = None, tid: str = Depends(rate_limit)) -> dict:
    return pipeline.briefing(lang, tenant_id=tid)


@app.get("/sessions")
def sessions(tid: str = Depends(rate_limit)) -> dict:
    return {"sessions": [s.__dict__ for s in pipeline.store.list_sessions(tid)]}


@app.delete("/data")
def delete_all(tid: str = Depends(resolve_tenant)) -> dict:
    # Privacy operations bypass the rate limiter — never make "delete me" wait.
    return {"deleted_segments": pipeline.delete_all(tid)}


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str, tid: str = Depends(resolve_tenant)) -> dict:
    return {
        "deleted_segments": pipeline.delete_session(session_id, tid),
        "session_id": session_id,
    }


@app.get("/usage")
def usage(tid: str = Depends(resolve_tenant)) -> dict:
    return pipeline.usage.get(tid)


# ---- consent + region gating -------------------------------------------------
@app.get("/consent")
def consent_status(tid: str = Depends(resolve_tenant)) -> dict:
    return pipeline.consent(tid).status()


@app.post("/consent/{scope}")
def consent_record(scope: str, body: ConsentBody,
                   tid: str = Depends(resolve_tenant)) -> dict:
    return pipeline.consent(tid).record(scope, body.granted, body.reason)


# ---- billing -----------------------------------------------------------------
@app.get("/billing")
def billing_status(tid: str = Depends(resolve_tenant)) -> dict:
    from .billing import PLAN_CATALOG
    sub = pipeline.subscriptions.get(tid)
    return {"subscription": sub.to_dict(), "catalog": PLAN_CATALOG}


@app.post("/billing/start-trial")
def billing_start_trial(tid: str = Depends(resolve_tenant)) -> dict:
    return pipeline.subscriptions.start_trial(tid).to_dict()


@app.post("/billing/subscribe")
def billing_subscribe(body: SubscribeBody,
                      tid: str = Depends(rate_limit)) -> dict:
    from .billing import PLAN_CATALOG
    if body.plan not in PLAN_CATALOG:
        raise HTTPException(status_code=400, detail=f"unknown plan: {body.plan!r}")
    return pipeline.billing.create_payment(plan=body.plan, tenant_id=tid, annual=body.annual)


@app.post("/billing/webhook/{provider}")
async def billing_webhook(provider: str, body: dict) -> dict:
    """Provider-callback endpoint. Not rate-limited (the provider's own infra calls us)."""
    if pipeline.billing.name != provider:
        raise HTTPException(
            status_code=400,
            detail=f"this server is configured for billing {pipeline.billing.name!r}, "
                   f"got webhook for {provider!r}",
        )
    parsed = pipeline.billing.handle_webhook(body)
    if parsed["verb"] == "paid":
        sub = pipeline.subscriptions.activate(
            parsed["tenant_id"], parsed["plan"], provider=provider,
            annual=bool(body.get("annual", False)),
        )
    elif parsed["verb"] == "failed":
        sub = pipeline.subscriptions.mark_past_due(parsed["tenant_id"])
    else:
        raise HTTPException(status_code=400, detail=f"unknown webhook verb: {parsed['verb']!r}")
    return {"ok": True, "subscription": sub.to_dict()}


# ---- API key management ------------------------------------------------------
@app.post("/apikeys")
def apikey_create(body: ApiKeyBody, tid: str = Depends(resolve_tenant)) -> dict:
    """Mint a new API key for the caller. The plaintext `api_key` field is shown
    ONCE — store it client-side immediately. Subsequent /apikeys responses only show
    the masked form.

    Bootstrap: this endpoint accepts X-User-Id as caller identity so a brand-new tenant
    can create their first key without already having one."""
    plaintext, rec = pipeline.api_keys.create(tid, label=body.label or "")
    return {
        "api_key": plaintext,
        "key_id": rec.key_id,
        "label": rec.label,
        "masked": rec.masked,
        "created_at": rec.created_at,
        "warning": "Store this api_key now — it is not retrievable later.",
    }


@app.get("/apikeys")
def apikey_list(tid: str = Depends(resolve_tenant)) -> dict:
    return {"keys": pipeline.api_keys.list_for_tenant(tid)}


@app.delete("/apikeys/{key_id}")
def apikey_revoke(key_id: str, tid: str = Depends(resolve_tenant)) -> dict:
    ok = pipeline.api_keys.revoke(key_id, tid)
    if not ok:
        # Same shape as a successful revoke — no info leak about whether the id exists.
        return {"revoked": False, "key_id": key_id}
    return {"revoked": True, "key_id": key_id}


# ---- owner-voice enrollment --------------------------------------------------
# Voiceprint stays local (residency-compliant). The reference clip is consumed to compute
# the embedding and then dropped — we never store raw enrollment audio.
@app.get("/enroll/owner")
def enroll_status(tid: str = Depends(resolve_tenant)) -> dict:
    return pipeline.owner(tid).status()


@app.post("/enroll/owner")
async def enroll_owner(file: UploadFile = File(...),
                       tid: str = Depends(rate_limit)) -> dict:
    if pipeline.diarizer is None:
        raise HTTPException(
            status_code=400,
            detail="Owner enrollment requires a diarizer. Set OMNI_DIARIZER=mock|pyannote.",
        )
    audio = await file.read()
    voiceprint = pipeline.diarizer.embed_voice(audio)
    if not voiceprint:
        raise HTTPException(status_code=400, detail="Could not embed the reference clip.")
    return pipeline.owner(tid).enroll([voiceprint])


@app.delete("/enroll/owner")
def enroll_clear(tid: str = Depends(resolve_tenant)) -> dict:
    pipeline.owner(tid).clear()
    return {"enrolled": False}
