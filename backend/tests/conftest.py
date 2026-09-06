import os

os.environ.setdefault("API_BEARER_TOKEN", "test-token")
os.environ.setdefault("LLM_PROVIDER", "mock")

import pytest
from fastapi.testclient import TestClient

from backend.api import dependencies as deps
from backend.core.embeddings import MockEmbeddingModel
from backend.core.llm_client import MockLLMClient
from backend.core.rag_pipeline import BM25SparseIndex, RagPipeline
from backend.core.vector_store import VectorStore
from backend.main import app
from backend.utils.taxonomy_client import InMemoryCache, TaxonomyClient


@pytest.fixture
def test_vector_store():
    return VectorStore(collection_name="api_test_collection", vector_size=768)


@pytest.fixture
def test_pipeline(test_vector_store):
    taxonomy_client = TaxonomyClient(
        gbif_api_base="https://api.gbif.org/v1",
        pbdb_api_base="https://paleobiodb.org/data1.2",
        cache=InMemoryCache(),
    )
    return RagPipeline(
        embedding_model=MockEmbeddingModel(dimension=768),
        vector_store=test_vector_store,
        llm_client=MockLLMClient(canned_response="Answer with citation [seed:0]."),
        taxonomy_client=taxonomy_client,
        sparse_index=BM25SparseIndex(),
        top_k=5,
    )


@pytest.fixture
def client(test_pipeline, test_vector_store):
    app.dependency_overrides[deps.get_rag_pipeline] = lambda: test_pipeline
    app.dependency_overrides[deps.get_vector_store] = lambda: test_vector_store
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token"}
