import json

import pytest

from backend.core.embeddings import MockEmbeddingModel
from backend.core.llm_client import MockLLMClient
from backend.core.rag_pipeline import BM25SparseIndex, RagPipeline
from backend.core.vector_store import VectorStore
from backend.utils.taxonomy_client import InMemoryCache, TaxonomyClient
from eval.run_eval import evaluate_citation_faithfulness, evaluate_recall_at_k, load_golden_set


@pytest.fixture
def seeded_pipeline():
    store = VectorStore(collection_name="eval_test_collection", vector_size=768)
    embedding_model = MockEmbeddingModel(dimension=768)

    vector = embedding_model.embed(["smilodon population genetics evidence"])[0]
    store.upsert_chunks(
        [
            {
                "id": "docA::0",
                "dense_vector": vector,
                "payload": {
                    "doc_id": "docA",
                    "chunk_index": 0,
                    "section": "Results",
                    "chunk_type": "text",
                    "chunk_text": "Smilodon fatalis population genetics evidence.",
                    "content_hash": "h0",
                },
            }
        ]
    )

    taxonomy_client = TaxonomyClient(
        gbif_api_base="https://api.gbif.org/v1", pbdb_api_base="https://paleobiodb.org/data1.2", cache=InMemoryCache()
    )
    return RagPipeline(
        embedding_model=embedding_model,
        vector_store=store,
        llm_client=MockLLMClient(canned_response="Evidence found here [docA:0]."),
        taxonomy_client=taxonomy_client,
        sparse_index=BM25SparseIndex(),
        top_k=5,
    )


def test_load_golden_set_parses_jsonl(tmp_path):
    path = tmp_path / "golden.jsonl"
    path.write_text(
        json.dumps({"question": "q1", "expected_source_doc_ids": ["docA"], "expected_answer_contains": ["x"]}) + "\n"
    )
    examples = load_golden_set(path)
    assert len(examples) == 1
    assert examples[0].question == "q1"


@pytest.mark.asyncio
async def test_recall_at_k_scores_correctly_against_seeded_corpus(seeded_pipeline):
    from eval.run_eval import GoldenExample

    examples = [
        GoldenExample(question="smilodon population genetics evidence", expected_source_doc_ids=["docA"], expected_answer_contains=[]),
        GoldenExample(question="unrelated question", expected_source_doc_ids=["docZ_never_ingested"], expected_answer_contains=[]),
    ]
    result = await evaluate_recall_at_k(seeded_pipeline, examples, k=5)

    assert result["hits"] == 1
    assert result["recall_at_k"] == 0.5


@pytest.mark.asyncio
async def test_citation_faithfulness_flags_answers_with_no_retrieved_support():
    # Use a pipeline whose store is empty, so the mock LLM's citation is
    # guaranteed hallucinated relative to what's retrieved.
    from eval.run_eval import GoldenExample

    empty_store = VectorStore(collection_name="eval_empty_collection", vector_size=768)
    taxonomy_client = TaxonomyClient(
        gbif_api_base="https://api.gbif.org/v1", pbdb_api_base="https://paleobiodb.org/data1.2", cache=InMemoryCache()
    )
    pipeline = RagPipeline(
        embedding_model=MockEmbeddingModel(dimension=768),
        vector_store=empty_store,
        llm_client=MockLLMClient(canned_response="Fabricated claim [docA:0]."),
        taxonomy_client=taxonomy_client,
        sparse_index=BM25SparseIndex(),
        top_k=5,
    )
    examples = [GoldenExample(question="anything", expected_source_doc_ids=["docA"], expected_answer_contains=[])]

    result = await evaluate_citation_faithfulness(pipeline, examples)

    assert result["answers_with_hallucinated_citations"] == 1
    assert result["faithfulness_rate"] == 0.0
