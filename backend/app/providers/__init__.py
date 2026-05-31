"""Factory: build providers from settings. Defaults to offline mocks."""
from __future__ import annotations

from ..config import Settings
from .base import Diarizer, EmbeddingProvider, LLMProvider, STTProvider
from .mock import HashingEmbedding, MockDiarizer, MockLLM, MockSTT


def make_stt(s: Settings) -> STTProvider:
    if s.stt_provider == "yandex":
        from .yandex_stt import YandexSTT
        return YandexSTT(s.yandex_api_key, s.yandex_folder_id)
    return MockSTT()


def make_embedding(s: Settings) -> EmbeddingProvider:
    if s.embed_provider == "openai":
        from .llm_openai import OpenAIEmbedding
        return OpenAIEmbedding(
            s.openai_api_key, s.openai_base_url, s.openai_embed_model, s.embedding_dim,
        )
    if s.embed_provider == "local":
        from .embed_local import LocalSentenceTransformerEmbedding
        return LocalSentenceTransformerEmbedding(s.local_embed_model, s.local_embed_device)
    return HashingEmbedding(s.embedding_dim)


def make_llm(s: Settings) -> LLMProvider:
    if s.llm_provider == "anthropic":
        from .llm_anthropic import AnthropicLLM
        return AnthropicLLM(s.anthropic_api_key, s.anthropic_model, s.anthropic_version)
    if s.llm_provider == "openai":
        from .llm_openai import OpenAILLM
        return OpenAILLM(s.openai_api_key, s.openai_base_url, s.openai_chat_model)
    return MockLLM()


def make_diarizer(s: Settings) -> Diarizer | None:
    """Return the configured diarizer, or None when diarization is disabled (default).

    None means the pipeline keeps STT's own speaker labels — exactly the pre-task-2
    behavior. The offline tests run with the mock diarizer.
    """
    if s.diarizer_provider == "mock":
        return MockDiarizer()
    if s.diarizer_provider == "pyannote":
        from .diarize_pyannote import PyannoteDiarizer
        return PyannoteDiarizer(s.hf_token, s.diarizer_device)
    return None
