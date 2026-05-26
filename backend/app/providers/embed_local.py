"""Local, self-hosted embeddings via sentence-transformers (HuggingFace).

Used when OMNI_EMBED=local. The default model is BGE-M3 — multilingual (100+ languages
including Russian and Uzbek), strong retrieval quality, 1024-dim. Alternatives that work
without code changes: intfloat/multilingual-e5-large (1024-dim), intfloat/multilingual-e5-
base (768-dim). Pick via OMNI_LOCAL_EMBED_MODEL.

Why this matters for Omnisense: the residency plan keeps voice + raw audio + voiceprints
in-country. Embeddings sit between raw audio and the cross-border LLM call — running them
locally means semantic recall over Uzbek/Russian transcripts never leaves Uzbekistan.

Import is lazy so the offline test suite (where HuggingFace is blocked) does not pay the
import cost. The first `embed()` call downloads weights (~2GB for BGE-M3); cache them in
the team's environment via HF_HOME or the docker image.
"""
from __future__ import annotations

from .base import EmbeddingProvider


class LocalSentenceTransformerEmbedding(EmbeddingProvider):
    def __init__(self, model_name: str, device: str = "cpu") -> None:
        from sentence_transformers import SentenceTransformer  # lazy: HF needed only here

        self.model_name = model_name
        self._model = SentenceTransformer(model_name, device=device)
        self._dim = int(self._model.get_sentence_embedding_dimension())

    @property
    def dim(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        # normalize_embeddings=True so cosine search (the default in our pgvector index) is
        # equivalent to a plain dot-product — and stays consistent with the in-memory store's
        # cosine helper.
        vectors = self._model.encode(
            texts, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False
        )
        return [list(map(float, row)) for row in vectors]
