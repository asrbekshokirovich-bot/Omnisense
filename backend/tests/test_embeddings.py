"""Tests for the embedding providers and how the pipeline wires them to the store.

These all run offline. The local sentence-transformers path is exercised by injecting a
fake `sentence_transformers` module into sys.modules — so we never download weights or
hit HuggingFace (which is blocked in this sandbox anyway).
"""
from __future__ import annotations

import sys
import types

import pytest


# ---- HashingEmbedding (mock) --------------------------------------------
def test_hashing_embedding_dim_is_configurable():
    from app.providers.mock import HashingEmbedding

    e = HashingEmbedding(dim=128)
    assert e.dim == 128
    vectors = e.embed(["salom dunyo", "привет мир", "hello world"])
    assert len(vectors) == 3
    assert all(len(v) == 128 for v in vectors)


# ---- LocalSentenceTransformerEmbedding ----------------------------------
class _FakeSTModel:
    """Stands in for sentence_transformers.SentenceTransformer — same surface we use."""

    def __init__(self, name: str, device: str = "cpu") -> None:
        self.name = name
        self.device = device

    def get_sentence_embedding_dimension(self) -> int:
        return 1024  # match BGE-M3

    def encode(self, texts, **kwargs):
        # Return a normalized-ish list-of-lists; encode() in our adapter calls list(map(float, ...))
        # so the rows just need to be iterable of numbers.
        return [[float(i) / 1024.0] * 1024 for i, _ in enumerate(texts, start=1)]


@pytest.fixture
def fake_sentence_transformers(monkeypatch):
    """Inject a fake sentence_transformers module so the local provider imports cleanly."""
    fake = types.ModuleType("sentence_transformers")
    fake.SentenceTransformer = _FakeSTModel
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake)
    # Drop any cached import of our adapter so the lazy `from sentence_transformers import …`
    # binds to the fake.
    sys.modules.pop("app.providers.embed_local", None)


def test_local_embedding_reports_model_dim(fake_sentence_transformers):
    from app.providers.embed_local import LocalSentenceTransformerEmbedding

    e = LocalSentenceTransformerEmbedding("BAAI/bge-m3", device="cpu")
    assert e.dim == 1024
    out = e.embed(["uchrashuv qachon?", "когда встреча?"])
    assert len(out) == 2
    assert all(len(v) == 1024 for v in out)
    # Records the model so the factory wiring is observable.
    assert e.model_name == "BAAI/bge-m3"


# ---- Factory dispatch ---------------------------------------------------
def test_factory_returns_mock_by_default():
    from app.config import Settings
    from app.providers import make_embedding
    from app.providers.mock import HashingEmbedding

    e = make_embedding(Settings(embed_provider="mock", embedding_dim=256))
    assert isinstance(e, HashingEmbedding)
    assert e.dim == 256


def test_factory_builds_openai_with_configured_dim(monkeypatch):
    from app.config import Settings
    from app.providers import make_embedding
    from app.providers.llm_openai import OpenAIEmbedding

    s = Settings(
        embed_provider="openai",
        embedding_dim=1024,
        openai_api_key="k",
        openai_base_url="https://tei.local",          # self-hosted TEI endpoint
        openai_embed_model="BAAI/bge-m3",
    )
    e = make_embedding(s)
    assert isinstance(e, OpenAIEmbedding)
    assert e.dim == 1024
    assert e.model == "BAAI/bge-m3"


def test_factory_builds_local(fake_sentence_transformers):
    from app.config import Settings
    from app.providers import make_embedding
    from app.providers.embed_local import LocalSentenceTransformerEmbedding

    s = Settings(
        embed_provider="local",
        local_embed_model="BAAI/bge-m3",
        local_embed_device="cpu",
    )
    e = make_embedding(s)
    assert isinstance(e, LocalSentenceTransformerEmbedding)
    assert e.dim == 1024


# ---- Pipeline-level: embedder dim propagates to the store ----------------
def test_pipeline_passes_embedder_dim_to_store(fake_sentence_transformers, monkeypatch):
    """End-to-end: when OMNI_EMBED=local, the pgvector store must be sized to 1024
    (BGE-M3), not the 256 default OMNI_EMBED_DIM. We intercept make_store to capture the
    dim argument without needing a real Postgres."""
    from app.config import Settings
    from app.pipeline import Pipeline

    captured: dict = {}

    def fake_make_store(s, dim=None):
        captured["dim"] = dim
        from app.store.memory import InMemoryStore
        return InMemoryStore()

    monkeypatch.setattr("app.pipeline.make_store", fake_make_store)

    Pipeline(Settings(embed_provider="local", local_embed_model="BAAI/bge-m3"))
    assert captured["dim"] == 1024


def test_pipeline_uses_default_dim_for_mock(monkeypatch):
    from app.config import Settings
    from app.pipeline import Pipeline

    captured: dict = {}

    def fake_make_store(s, dim=None):
        captured["dim"] = dim
        from app.store.memory import InMemoryStore
        return InMemoryStore()

    monkeypatch.setattr("app.pipeline.make_store", fake_make_store)

    Pipeline(Settings(embed_provider="mock", embedding_dim=256))
    assert captured["dim"] == 256
