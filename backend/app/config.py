"""Environment-driven configuration. Defaults are offline/mock so the loop runs with zero setup.

No secrets live in code — real provider keys come from the environment (see .env.example).
"""
from __future__ import annotations

import os
from dataclasses import dataclass


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


@dataclass(frozen=True)
class Settings:
    # Provider selection: "mock" (offline default) or a real adapter name.
    stt_provider: str = _env("OMNI_STT", "mock")          # mock | yandex
    embed_provider: str = _env("OMNI_EMBED", "mock")      # mock | openai
    llm_provider: str = _env("OMNI_LLM", "mock")          # mock | anthropic | openai
    store_backend: str = _env("OMNI_STORE", "memory")     # memory | pgvector

    embedding_dim: int = int(_env("OMNI_EMBED_DIM", "256"))
    default_lang: str = _env("OMNI_DEFAULT_LANG", "ru")
    retrieval_top_k: int = int(_env("OMNI_TOP_K", "5"))

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
