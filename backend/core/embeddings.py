"""
Embedding model interface, swappable via EMBEDDING_MODEL_NAME (backend/config.py)
without touching any calling code — required because the implementation plan
calls for an empirical PubMedBERT-vs-general-purpose-model comparison in the
eval harness (see eval/run_eval.py).

NOTE: `sentence-transformers` / `torch` were not installed in the build
sandbox (no network path to the model hub there). This module is written and
structured correctly but the real `SentenceTransformerEmbeddingModel` has not
been executed end-to-end. `MockEmbeddingModel` below IS exercised by the
test suite so calling code (vector_store, rag_pipeline) is verified against
the real interface shape. See HANDOFF.md step 1.
"""
from __future__ import annotations

import hashlib
import random
from abc import ABC, abstractmethod


class EmbeddingModel(ABC):
    @property
    @abstractmethod
    def dimension(self) -> int: ...

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class SentenceTransformerEmbeddingModel(EmbeddingModel):
    """Real embedding backend. Requires `sentence-transformers` + `torch`
    installed and network access to the model hub (or a pre-downloaded model
    cache) on first load. NOT exercised in the build sandbox — verify on the
    target machine per HANDOFF.md."""

    def __init__(self, model_name: str, batch_size: int = 32) -> None:
        from sentence_transformers import SentenceTransformer  # deferred import

        self.model_name = model_name
        self.batch_size = batch_size
        self._model = SentenceTransformer(model_name)

    @property
    def dimension(self) -> int:
        return self._model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(
            texts, batch_size=self.batch_size, show_progress_bar=False, normalize_embeddings=True
        )
        return vectors.tolist()


class MockEmbeddingModel(EmbeddingModel):
    """Deterministic pseudo-embedding for tests and for environments without
    model-hub access. NOT semantically meaningful — produces a stable
    hash-seeded vector per input text so tests can assert on shape,
    determinism, and pipeline wiring without needing real model weights."""

    def __init__(self, dimension: int = 768) -> None:
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) % (2**32)
            rng = random.Random(seed)
            vectors.append([rng.uniform(-1, 1) for _ in range(self._dimension)])
        return vectors


def build_embedding_model(model_name: str, batch_size: int = 32, use_mock: bool = False) -> EmbeddingModel:
    if use_mock:
        return MockEmbeddingModel()
    return SentenceTransformerEmbeddingModel(model_name=model_name, batch_size=batch_size)
