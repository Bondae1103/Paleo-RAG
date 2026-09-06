from pathlib import Path
import json
import pytest

from backend.core.chunking import Block, ChunkType
from backend.core.vector_store import VectorStore
from backend.workers.tasks import (
    _extract_document_metadata,
    chunk_document_task,
    dedup_check_task,
    embed_chunks_task,
    upsert_to_qdrant_task,
)


def test_extract_document_metadata_from_manifest(tmp_path, monkeypatch):
    manifest_file = tmp_path / "manifest.jsonl"
    manifest_file.write_text(
        json.dumps({
            "doc_id": "docTest1",
            "doi": "10.1000/182",
            "title": "Ancient DNA of Mammuthus primigenius in Late Pleistocene",
            "publication_year": 2021,
            "taxon_scientific_name": "Mammuthus primigenius",
            "geological_period": "Late Pleistocene",
        }) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("backend.workers.tasks.MANIFEST_PATH", manifest_file)

    meta = _extract_document_metadata("docTest1", "dummy.pdf")
    assert meta["doi"] == "10.1000/182"
    assert meta["publication_year"] == 2021
    assert meta["taxon_scientific_name"] == "Mammuthus primigenius"
    assert meta["geological_period"] == "Late Pleistocene"


def test_tasks_pipeline_metadata_propagation(tmp_path, monkeypatch):
    # Setup test memory vector store
    store = VectorStore(collection_name="test_tasks_collection", vector_size=16)

    # Mock VectorStore inside tasks to use our in-memory store
    monkeypatch.setattr(
        "backend.workers.tasks.VectorStore",
        lambda *args, **kwargs: store,
    )

    # Mock build_embedding_model to return fixed 16-dim vectors
    class FakeEmbeddingModel:
        def embed(self, texts):
            return [[0.1] * 16 for _ in texts]

    monkeypatch.setattr(
        "backend.workers.tasks.build_embedding_model",
        lambda *args, **kwargs: FakeEmbeddingModel(),
    )

    parsed = {
        "doc_id": "docTest2",
        "blocks": [
            {
                "text": "Mammuthus primigenius was a species of mammoth that lived during the Pleistocene epoch.",
                "section": "Introduction",
                "block_type": "text",
                "page_number": 1,
            }
        ],
        "metadata": {
            "doi": "10.1038/nature12345",
            "title": "Mammoth Genomics",
            "publication_year": 2023,
            "taxon_scientific_name": "Mammuthus primigenius",
            "geological_period": "Pleistocene",
        },
    }

    chunked = chunk_document_task(parsed)
    assert len(chunked["chunks"]) == 1
    assert chunked["metadata"]["publication_year"] == 2023

    deduped = dedup_check_task(chunked)
    assert len(deduped["chunks_to_upsert"]) == 1
    assert deduped["metadata"]["taxon_scientific_name"] == "Mammuthus primigenius"

    embedded = embed_chunks_task(deduped)
    assert len(embedded["vectors"]) == 1
    assert embedded["metadata"]["geological_period"] == "Pleistocene"

    upsert_res = upsert_to_qdrant_task(embedded)
    assert upsert_res["upserted"] == 1

    # Verify point payload in store
    corpus = store.scroll_all_chunks()
    assert len(corpus) == 1
    assert corpus[0][0] == ("docTest2", 0)

    # Query with filter
    from backend.core.vector_store import SearchFilters
    res = store.dense_search(
        [0.1] * 16,
        top_k=5,
        filters=SearchFilters(
            taxon_scientific_name="Mammuthus primigenius",
            geological_period="Pleistocene",
            publication_year_min=2020,
        ),
    )
    assert len(res) == 1
    assert res[0].doc_id == "docTest2"
