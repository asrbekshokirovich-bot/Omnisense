"""API request/response models."""
from __future__ import annotations

from pydantic import BaseModel, Field


class IngestTextRequest(BaseModel):
    text: str = Field(..., min_length=1)
    lang: str = "ru"
    source: str = "text"
    speaker: str = "owner"


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    lang: str | None = None
    # Optional recall filters — narrow to a meeting or a time window without losing the
    # rest of memory. (lang is intentionally NOT a recall filter; it only steers the reply.)
    session_id: str | None = None
    since: float | None = None
    until: float | None = None


class Citation(BaseModel):
    session_id: str
    speaker: str
    start_ms: int
    timestamp: str
    text: str
    score: float | None = None


class AskResponse(BaseModel):
    question: str
    answer: str
    citations: list[Citation]


class IngestResponse(BaseModel):
    session_id: str
    segments: int
