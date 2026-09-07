"""
FastAPI dependencies: bearer-token auth and shared singleton clients
(vector store, embedding model, LLM client, taxonomy client).

Clients are built lazily and cached at module scope so the app can start
even when some backends (Qdrant server, Ollama) aren't reachable yet — the
error surfaces only when the specific endpoint that needs that backend is
called, and /api/health reports per-dependency status explicitly.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Optional

from fastapi import Header, HTTPException, status

from backend.config import Settings, get_settings
from backend.core.embeddings import EmbeddingModel, build_embedding_model
from backend.core.llm_client import LLMClient, build_llm_client
from backend.core.rag_pipeline import BM25SparseIndex, RagPipeline
from backend.core.vector_store import VectorStore
from backend.utils.taxonomy_client import TaxonomyClient


async def verify_bearer_token(authorization: str = Header(default="")) -> None:
    settings = get_settings()
    expected = f"Bearer {settings.api_bearer_token}"
    if authorization != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API token.")


@lru_cache
def get_vector_store() -> VectorStore:
    settings = get_settings()
    return VectorStore(
        collection_name=settings.qdrant_collection_name,
        url=None if settings.qdrant_use_local_mode else settings.qdrant_url,
        local_path=settings.qdrant_local_path if settings.qdrant_use_local_mode else None,
        vector_size=settings.embedding_dimension,
    )


@lru_cache
def get_embedding_model() -> EmbeddingModel:
    settings = get_settings()
    # use_mock is intentionally NOT wired to a settings flag here — this
    # function is expected to be overridden by the test suite (see
    # backend/tests/test_api.py) via FastAPI's dependency_overrides, so
    # production code always attempts the real model.
    return build_embedding_model(settings.embedding_model_name, settings.embedding_batch_size)


@lru_cache
def get_llm_client() -> LLMClient:
    settings = get_settings()
    return build_llm_client(
        provider=settings.llm_provider,
        ollama_base_url=settings.ollama_base_url,
        ollama_model=settings.ollama_model,
        anthropic_api_key=settings.anthropic_api_key,
        anthropic_model=settings.anthropic_model,
    )


@lru_cache
def get_taxonomy_client() -> TaxonomyClient:
    settings = get_settings()
    return TaxonomyClient(
        gbif_api_base=settings.gbif_api_base,
        pbdb_api_base=settings.pbdb_api_base,
        cache_ttl_seconds=settings.taxonomy_cache_ttl_seconds,
    )


@lru_cache
def get_sparse_index() -> BM25SparseIndex:
    index = BM25SparseIndex()
    try:
        store = get_vector_store()
        index.sync_from_vector_store(store)
    except Exception:
        pass
    return index


@lru_cache
def get_reranker() -> Optional[Any]:
    settings = get_settings()
    if not settings.reranker_enabled:
        return None
    try:
        from sentence_transformers import CrossEncoder

        return CrossEncoder(settings.reranker_model_name)
    except Exception:
        return None


def get_rag_pipeline() -> RagPipeline:
    settings = get_settings()
    return RagPipeline(
        embedding_model=get_embedding_model(),
        vector_store=get_vector_store(),
        llm_client=get_llm_client(),
        taxonomy_client=get_taxonomy_client(),
        sparse_index=get_sparse_index(),
        top_k=settings.retrieval_top_k,
        reranker=get_reranker(),
        reranker_enabled=settings.reranker_enabled,
    )
