"""Factory: build providers from settings. Defaults to offline mocks."""
from __future__ import annotations

from ..config import Settings
from .base import EmbeddingProvider, LLMProvider, STTProvider
from .mock import HashingEmbedding, MockLLM, MockSTT


def make_stt(s: Settings) -> STTProvider:
    if s.stt_provider == "yandex":
        from .yandex_stt import YandexSTT
        return YandexSTT(s.yandex_api_key, s.yandex_folder_id)
    return MockSTT()


def make_embedding(s: Settings) -> EmbeddingProvider:
    if s.embed_provider == "openai":
        from .llm_openai import OpenAIEmbedding
        return OpenAIEmbedding(s.openai_api_key, s.openai_base_url, s.openai_embed_model)
    return HashingEmbedding(s.embedding_dim)


def make_llm(s: Settings) -> LLMProvider:
    if s.llm_provider == "openai":
        from .llm_openai import OpenAILLM
        return OpenAILLM(s.openai_api_key, s.openai_base_url, s.openai_chat_model)
    return MockLLM()
