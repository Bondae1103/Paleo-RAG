from backend.core.rag_pipeline import build_prompt, check_citations
from backend.core.vector_store import SearchResult


def _chunk(doc_id: str, idx: int, text: str) -> SearchResult:
    return SearchResult(doc_id=doc_id, chunk_index=idx, section="Results", chunk_type="text", text=text, score=0.9)


def test_check_citations_flags_hallucinated_marker():
    retrieved = [_chunk("docA", 0, "real content")]
    answer = "This is supported by the literature [docA:0] and also by [docZ:9]."

    warnings = check_citations(answer, retrieved)

    assert len(warnings) == 1
    assert warnings[0].cited_marker == "[docZ:9]"


def test_check_citations_passes_when_all_markers_valid():
    retrieved = [_chunk("docA", 0, "text"), _chunk("docA", 1, "more text")]
    answer = "Fact one [docA:0]. Fact two [docA:1]."

    warnings = check_citations(answer, retrieved)

    assert warnings == []


def test_build_prompt_includes_context_and_question():
    retrieved = [_chunk("docA", 0, "Smilodon fatalis population genetics evidence.")]
    prompt = build_prompt("What is known about Smilodon population decline?", retrieved)

    assert "Smilodon fatalis population genetics evidence." in prompt
    assert "What is known about Smilodon population decline?" in prompt
    assert "[docA:0]" in prompt
    assert "does not address this" in prompt  # instruction present, not fabricating


def test_bm25_sparse_index_sync_from_vector_store():
    from backend.core.embeddings import MockEmbeddingModel
    from backend.core.llm_client import MockLLMClient
    from backend.core.rag_pipeline import BM25SparseIndex, RagPipeline
    from backend.core.vector_store import VectorStore
    from backend.utils.taxonomy_client import InMemoryCache, TaxonomyClient

    store = VectorStore(collection_name="bm25_test_collection", vector_size=768)
    store.upsert_chunks(
        [
            {
                "id": "doc1::0",
                "dense_vector": [0.1] * 768,
                "payload": {
                    "doc_id": "doc1",
                    "chunk_index": 0,
                    "section": "Results",
                    "chunk_type": "text",
                    "chunk_text": "Ancient mitochondrial DNA from permafrost mammoths.",
                    "content_hash": "h1",
                },
            },
            {
                "id": "doc2::0",
                "dense_vector": [0.2] * 768,
                "payload": {
                    "doc_id": "doc2",
                    "chunk_index": 0,
                    "section": "Results",
                    "chunk_type": "text",
                    "chunk_text": "Holocene bison population dynamics across Eurasia.",
                    "content_hash": "h2",
                },
            },
        ]
    )

    sparse_index = BM25SparseIndex()
    assert sparse_index.rank(["mammoths"], top_k=2) == []  # Unbuilt index returns empty

    sparse_index.sync_from_vector_store(store)
    ranking = sparse_index.rank(["mammoths"], top_k=2)
    assert len(ranking) > 0
    assert ranking[0] == ("doc1", 0)


def test_rag_pipeline_auto_syncs_uninitialized_bm25_index():
    from backend.core.embeddings import MockEmbeddingModel
    from backend.core.llm_client import MockLLMClient
    from backend.core.rag_pipeline import BM25SparseIndex, RagPipeline
    from backend.core.vector_store import VectorStore
    from backend.utils.taxonomy_client import InMemoryCache, TaxonomyClient

    store = VectorStore(collection_name="pipeline_bm25_auto_sync", vector_size=768)
    store.upsert_chunks(
        [
            {
                "id": "docP::0",
                "dense_vector": [0.05] * 768,
                "payload": {
                    "doc_id": "docP",
                    "chunk_index": 0,
                    "section": "Results",
                    "chunk_type": "text",
                    "chunk_text": "Saber-toothed cat Smilodon fatalis bone collagen extraction.",
                    "content_hash": "hp",
                },
            }
        ]
    )

    empty_sparse_index = BM25SparseIndex()
    taxonomy_client = TaxonomyClient(
        gbif_api_base="https://api.gbif.org/v1", pbdb_api_base="https://paleobiodb.org/data1.2", cache=InMemoryCache()
    )
    pipeline = RagPipeline(
        embedding_model=MockEmbeddingModel(dimension=768),
        vector_store=store,
        llm_client=MockLLMClient(),
        taxonomy_client=taxonomy_client,
        sparse_index=empty_sparse_index,
        top_k=5,
    )

    # Calling retrieve should auto-sync the empty index
    expanded, results = pipeline.retrieve("Smilodon bone collagen")
    assert len(results) > 0
    assert results[0].doc_id == "docP"
    assert empty_sparse_index._bm25 is not None


def test_rag_pipeline_reranker_reorders_chunks():
    from backend.core.embeddings import MockEmbeddingModel
    from backend.core.llm_client import MockLLMClient
    from backend.core.rag_pipeline import BM25SparseIndex, RagPipeline
    from backend.core.vector_store import VectorStore
    from backend.utils.taxonomy_client import InMemoryCache, TaxonomyClient

    store = VectorStore(collection_name="pipeline_reranker_test", vector_size=768)
    store.upsert_chunks(
        [
            {
                "id": "doc1::0",
                "dense_vector": [0.1] * 768,
                "payload": {
                    "doc_id": "doc1",
                    "chunk_index": 0,
                    "section": "Results",
                    "chunk_type": "text",
                    "chunk_text": "Chunk with moderate relevance.",
                    "content_hash": "h1",
                },
            },
            {
                "id": "doc2::0",
                "dense_vector": [0.2] * 768,
                "payload": {
                    "doc_id": "doc2",
                    "chunk_index": 0,
                    "section": "Results",
                    "chunk_type": "text",
                    "chunk_text": "Chunk with highest reranker score.",
                    "content_hash": "h2",
                },
            },
        ]
    )

    class MockReranker:
        def predict(self, pairs):
            # Give doc2 chunk higher score regardless of initial order
            return [0.1 if "moderate" in pair[1] else 0.95 for pair in pairs]

    taxonomy_client = TaxonomyClient(
        gbif_api_base="https://api.gbif.org/v1", pbdb_api_base="https://paleobiodb.org/data1.2", cache=InMemoryCache()
    )
    pipeline = RagPipeline(
        embedding_model=MockEmbeddingModel(dimension=768),
        vector_store=store,
        llm_client=MockLLMClient(),
        taxonomy_client=taxonomy_client,
        sparse_index=BM25SparseIndex(),
        top_k=2,
        reranker=MockReranker(),
        reranker_enabled=True,
    )

    _, results = pipeline.retrieve("test query", top_k=2)
    assert len(results) == 2
    assert results[0].doc_id == "doc2"
    assert results[0].score == 0.95

