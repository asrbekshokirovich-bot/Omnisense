"""Environment-driven configuration. Defaults are offline/mock so the loop runs with zero setup.

No secrets live in code — real provider keys come from the environment (see .env.example).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _load_dotenv() -> None:
    """Load a local .env (backend/.env or cwd/.env) without overriding real env vars.
    Pure stdlib — no dependency. Runs before Settings is defined so field defaults see it."""
    for path in (Path.cwd() / ".env", Path(__file__).resolve().parent.parent / ".env"):
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))
        break


_load_dotenv()


@dataclass(frozen=True)
class Settings:
    # Provider selection: "mock" (offline default) or a real adapter name.
    stt_provider: str = _env("OMNI_STT", "mock")          # mock | yandex
    embed_provider: str = _env("OMNI_EMBED", "mock")      # mock | openai | local
    llm_provider: str = _env("OMNI_LLM", "mock")          # mock | anthropic | openai
    store_backend: str = _env("OMNI_STORE", "memory")     # memory | pgvector
    diarizer_provider: str = _env("OMNI_DIARIZER", "off") # off | mock | pyannote

    # Sizes the mock vector and the OpenAI-compatible vector. The `local` provider reports
    # its own dim from the loaded model (BGE-M3=1024, multilingual-e5-large=1024, etc).
    embedding_dim: int = int(_env("OMNI_EMBED_DIM", "256"))
    default_lang: str = _env("OMNI_DEFAULT_LANG", "ru")
    retrieval_top_k: int = int(_env("OMNI_TOP_K", "5"))

    # Local sentence-transformers embedder (in-country, no cross-border data path).
    local_embed_model: str = _env("OMNI_LOCAL_EMBED_MODEL", "BAAI/bge-m3")
    local_embed_device: str = _env("OMNI_LOCAL_EMBED_DEVICE", "cpu")

    # Owner-voice enrollment (centroid voiceprint stored locally; empty path = in-memory).
    owner_voiceprint_path: str = _env("OMNI_OWNER_VOICEPRINT_PATH", "")
    owner_match_threshold: float = float(_env("OMNI_OWNER_THRESHOLD", "0.7"))

    # Per-tenant consent log (append-only audit trail). Empty path = in-memory only.
    consent_log_path: str = _env("OMNI_CONSENT_LOG_PATH", "")

    # Billing provider (mock for Phase 0; payme/click adapters land with merchant
    # contracts). See app/billing.py + app/providers/billing_*.py.
    billing_provider: str = _env("OMNI_BILLING", "mock")  # mock | payme | click

    # Rate limiting (per-tenant token bucket; in-memory in Phase 0).
    rate_per_min: float = float(_env("OMNI_RATE_PER_MIN", "60"))
    rate_burst: float = float(_env("OMNI_RATE_BURST", "10"))

    # Encryption at rest (mock = passthrough; fernet = real, see app/encryption.py).
    encryption: str = _env("OMNI_ENCRYPTION", "mock")  # mock | fernet
    kek_b64: str = _env("OMNI_KEK", "")  # urlsafe-b64 32 bytes; required for fernet

    # Pyannote (when OMNI_DIARIZER=pyannote) — runtime needs the HF gated-model token.
    hf_token: str = _env("HF_TOKEN") or _env("HUGGING_FACE_HUB_TOKEN")
    diarizer_device: str = _env("OMNI_DIARIZER_DEVICE", "cpu")

    # Real-provider credentials / endpoints (only used when the matching provider is selected).
    yandex_api_key: str = _env("YANDEX_API_KEY")
    yandex_folder_id: str = _env("YANDEX_FOLDER_ID")

    # OpenAI-compatible endpoint (works for OpenAI, Azure, or a self-hosted gateway).
    openai_api_key: str = _env("OPENAI_API_KEY")
    openai_base_url: str = _env("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openai_chat_model: str = _env("OMNI_CHAT_MODEL", "gpt-4o-mini")
    openai_embed_model: str = _env("OMNI_EMBED_MODEL", "text-embedding-3-small")

    # Anthropic (Claude) — the reasoning/answer + briefing LLM.
    anthropic_api_key: str = _env("ANTHROPIC_API_KEY")
    anthropic_model: str = _env("OMNI_ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
    anthropic_version: str = _env("ANTHROPIC_VERSION", "2023-06-01")

    database_url: str = _env("DATABASE_URL", "postgresql://omni:omni@localhost:5432/omni")


settings = Settings()
