import random

from backend.core.vector_store import SearchFilters, VectorStore


def _fake_vector(seed: int, dim: int = 16) -> list[float]:
    rng = random.Random(seed)
    return [rng.uniform(-1, 1) for _ in range(dim)]


def _fresh_store() -> VectorStore:
    # ":memory:" mode: no Docker/Qdrant server required.
    return VectorStore(collection_name="test_collection", vector_size=16)


def test_upsert_and_dense_search_roundtrip():
    store = _fresh_store()
    points = [
        {
            "id": "docA::0",
            "dense_vector": _fake_vector(1),
            "payload": {
                "doc_id": "docA",
                "chunk_index": 0,
                "section": "Results",
                "chunk_type": "text",
                "chunk_text": "Smilodon fatalis population decline evidence.",
                "content_hash": "hash0",
                "taxon_scientific_name": "Smilodon fatalis",
                "publication_year": 2018,
            },
        },
    ]
    store.upsert_chunks(points)

    results = store.dense_search(_fake_vector(1), top_k=5)
    assert len(results) == 1
    assert results[0].doc_id == "docA"
    assert results[0].chunk_index == 0


def test_payload_filter_restricts_results_to_matching_taxon_and_year():
    store = _fresh_store()
    points = []
    taxa = ["Smilodon fatalis", "Mammuthus primigenius", "Smilodon fatalis", "Ursus arctos"]
    years = [2010, 2016, 2020, 2021]
    for i, (taxon, year) in enumerate(zip(taxa, years)):
        points.append(
            {
                "id": f"doc{i}::0",
                "dense_vector": _fake_vector(i + 10),
                "payload": {
                    "doc_id": f"doc{i}",
                    "chunk_index": 0,
                    "section": "Results",
                    "chunk_type": "text",
                    "chunk_text": f"Text about {taxon}",
                    "content_hash": f"hash{i}",
                    "taxon_scientific_name": taxon,
                    "publication_year": year,
                },
            }
        )
    store.upsert_chunks(points)

    filters = SearchFilters(taxon_scientific_name="Smilodon fatalis", publication_year_min=2015)
    # Query with an arbitrary vector — filtering must apply regardless of
    # semantic similarity ranking, per the implementation plan's acceptance
    # criterion for this phase.
    results = store.dense_search(_fake_vector(999), top_k=10, filters=filters)

    assert len(results) == 1
    assert results[0].doc_id == "doc2"  # Smilodon fatalis, year 2020


def test_get_existing_hashes_returns_stored_content_hashes():
    store = _fresh_store()
    points = [
        {
            "id": "docB::0",
            "dense_vector": _fake_vector(2),
            "payload": {
                "doc_id": "docB",
                "chunk_index": 0,
                "section": "Intro",
                "chunk_type": "text",
                "chunk_text": "text",
                "content_hash": "abc123",
            },
        },
        {
            "id": "docB::1",
            "dense_vector": _fake_vector(3),
            "payload": {
                "doc_id": "docB",
                "chunk_index": 1,
                "section": "Intro",
                "chunk_type": "text",
                "chunk_text": "text2",
                "content_hash": "def456",
            },
        },
    ]
    store.upsert_chunks(points)

    hashes = store.get_existing_hashes("docB")
    assert hashes == {0: "abc123", 1: "def456"}


def test_delete_chunks_removes_only_specified_indices():
    store = _fresh_store()
    points = [
        {
            "id": f"docC::{i}",
            "dense_vector": _fake_vector(20 + i),
            "payload": {
                "doc_id": "docC",
                "chunk_index": i,
                "section": "Intro",
                "chunk_type": "text",
                "chunk_text": f"text{i}",
                "content_hash": f"h{i}",
            },
        }
        for i in range(3)
    ]
    store.upsert_chunks(points)

    store.delete_chunks("docC", [1])
    remaining = store.get_existing_hashes("docC")

    assert remaining == {0: "h0", 2: "h2"}


def test_hybrid_search_fuses_dense_and_sparse_rankings():
    store = _fresh_store()
    points = [
        {
            "id": f"docD::{i}",
            "dense_vector": _fake_vector(30 + i),
            "payload": {
                "doc_id": "docD",
                "chunk_index": i,
                "section": "Results",
                "chunk_type": "text",
                "chunk_text": f"chunk {i}",
                "content_hash": f"hd{i}",
            },
        }
        for i in range(5)
    ]
    store.upsert_chunks(points)

    # Sparse ranking strongly favors chunk_index=4, which is likely to rank
    # low on the (arbitrary) dense side — RRF fusion should still surface it.
    sparse_ranking = [("docD", 4), ("docD", 3)]
    results = store.hybrid_search(_fake_vector(999), sparse_ranked_doc_keys=sparse_ranking, top_k=5)

    result_keys = [(r.doc_id, r.chunk_index) for r in results]
    assert ("docD", 4) in result_keys


def test_hybrid_search_retrieves_sparse_only_hits_not_in_dense_results():
    store = _fresh_store()
    points = [
        {
            "id": f"docE::{i}",
            "dense_vector": [0.9] * 16,  # Close to query vector
            "payload": {
                "doc_id": "docE",
                "chunk_index": i,
                "section": "Results",
                "chunk_type": "text",
                "chunk_text": f"dense chunk {i}",
                "content_hash": f"he{i}",
            },
        }
        for i in range(25)
    ]
    # Add a point whose dense vector is completely orthogonal/opposite (will not be in top-20 dense)
    sparse_only_point = {
        "id": "docSparse::0",
        "dense_vector": [-0.9] * 16,
        "payload": {
            "doc_id": "docSparse",
            "chunk_index": 0,
            "section": "Methods",
            "chunk_type": "text",
            "chunk_text": "Unique keyword ancient DNA extraction protocol",
            "content_hash": "hsparse0",
        },
    }
    points.append(sparse_only_point)
    store.upsert_chunks(points)

    # Sparse ranking has docSparse at #1
    sparse_ranking = [("docSparse", 0)]
    results = store.hybrid_search([0.9] * 16, sparse_ranked_doc_keys=sparse_ranking, top_k=5)

    result_keys = [(r.doc_id, r.chunk_index) for r in results]
    assert ("docSparse", 0) in result_keys
    sparse_hit = next(r for r in results if r.doc_id == "docSparse")
    assert sparse_hit.text == "Unique keyword ancient DNA extraction protocol"
    assert sparse_hit.section == "Methods"


def test_scroll_all_chunks():
    store = _fresh_store()
    points = [
        {
            "id": f"docF::{i}",
            "dense_vector": _fake_vector(50 + i),
            "payload": {
                "doc_id": "docF",
                "chunk_index": i,
                "section": "Results",
                "chunk_type": "text",
                "chunk_text": f"scroll text {i}",
                "content_hash": f"hf{i}",
            },
        }
        for i in range(3)
    ]
    store.upsert_chunks(points)

    chunks = store.scroll_all_chunks()
    assert len(chunks) == 3
    doc_indices = [k for k, _ in chunks]
    assert ("docF", 0) in doc_indices
    assert ("docF", 1) in doc_indices
    assert ("docF", 2) in doc_indices
