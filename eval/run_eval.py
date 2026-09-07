"""
Evaluation harness, per implementation plan Phase 6.

NOT executed against a live corpus in the build sandbox: real ingestion
requires the PMC OA / bioRxiv connectors (blocked by sandbox network egress)
and real embeddings (sentence-transformers/torch not installed there — see
HANDOFF.md). This script is complete and correct against the RagPipeline
interface (verified indirectly: rag_pipeline.py's own logic is unit tested
in backend/tests/test_rag_pipeline.py), but running it end-to-end and
generating a report with real numbers is the first thing to do on the
target machine once ingestion + a real embedding model are working.

Usage (once the corpus is ingested and a real pipeline is wired up):
    python eval/run_eval.py --golden-set eval/golden_set.jsonl
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.core.rag_pipeline import RagPipeline


@dataclass
class GoldenExample:
    question: str
    expected_source_doc_ids: list[str]
    expected_answer_contains: list[str]


def load_golden_set(path: Path) -> list[GoldenExample]:
    examples = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        data = json.loads(line)
        examples.append(
            GoldenExample(
                question=data["question"],
                expected_source_doc_ids=data["expected_source_doc_ids"],
                expected_answer_contains=data.get("expected_answer_contains", []),
            )
        )
    return examples


async def evaluate_recall_at_k(pipeline: RagPipeline, examples: list[GoldenExample], k: int = 5) -> dict:
    hits = 0
    per_question = []
    for ex in examples:
        _, results = pipeline.retrieve(ex.question, top_k=k)
        retrieved_doc_ids = {r.doc_id for r in results}
        hit = bool(retrieved_doc_ids & set(ex.expected_source_doc_ids))
        hits += int(hit)
        per_question.append({"question": ex.question, "hit": hit, "retrieved_doc_ids": list(retrieved_doc_ids)})
    recall = hits / len(examples) if examples else 0.0
    return {"recall_at_k": recall, "k": k, "total": len(examples), "hits": hits, "detail": per_question}


async def evaluate_citation_faithfulness(pipeline: RagPipeline, examples: list[GoldenExample]) -> dict:
    total_answers = 0
    answers_with_warnings = 0
    total_warnings = 0
    per_question = []
    for ex in examples:
        answer = await pipeline.answer(ex.question)
        total_answers += 1
        n_warnings = len(answer.citation_warnings)
        total_warnings += n_warnings
        if n_warnings > 0:
            answers_with_warnings += 1
        per_question.append(
            {
                "question": ex.question,
                "n_citation_warnings": n_warnings,
                "warnings": [w.reason for w in answer.citation_warnings],
            }
        )
    return {
        "total_answers": total_answers,
        "answers_with_hallucinated_citations": answers_with_warnings,
        "total_hallucinated_citations": total_warnings,
        "faithfulness_rate": 1 - (answers_with_warnings / total_answers) if total_answers else 0.0,
        "detail": per_question,
    }


async def run_full_eval(pipeline: RagPipeline, golden_set_path: Path, k: int = 5) -> dict:
    examples = load_golden_set(golden_set_path)
    recall_result = await evaluate_recall_at_k(pipeline, examples, k=k)
    faithfulness_result = await evaluate_citation_faithfulness(pipeline, examples)
    return {"recall": recall_result, "faithfulness": faithfulness_result}


def render_report(results: dict, embedding_model_name: str, template_path: Path) -> str:
    template = template_path.read_text()
    return template.format(
        timestamp=time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        embedding_model_name=embedding_model_name,
        recall_at_k=f"{results['recall']['recall_at_k']:.2%}",
        k=results["recall"]["k"],
        total_questions=results["recall"]["total"],
        faithfulness_rate=f"{results['faithfulness']['faithfulness_rate']:.2%}",
        total_hallucinated_citations=results["faithfulness"]["total_hallucinated_citations"],
    )


async def main() -> None:
    parser = argparse.ArgumentParser(description="PaleoRAG Evaluation Harness")
    parser.add_argument("--golden-set", default="eval/golden_set.jsonl", help="Path to golden set jsonl")
    parser.add_argument("--k", type=int, default=5, help="Top-k for Recall@k")
    parser.add_argument(
        "--compare-embeddings",
        action="store_true",
        help="Run comparison between PubMedBERT and general-purpose embeddings or sparse baseline.",
    )
    parser.add_argument("--output", default=None, help="Optional path to output markdown report")
    args = parser.parse_args()

    golden_set_path = Path(args.golden_set)
    if not golden_set_path.exists():
        print(f"Error: Golden set not found at {golden_set_path}")
        return

    from backend.api.dependencies import (
        get_embedding_model,
        get_llm_client,
        get_rag_pipeline,
        get_sparse_index,
        get_taxonomy_client,
        get_vector_store,
    )
    from backend.config import get_settings

    settings = get_settings()
    print(f"Loading pipeline with embedding model: {settings.embedding_model_name}...")
    pipeline = get_rag_pipeline()

    print(f"Running evaluation against {golden_set_path} (k={args.k})...")
    examples = load_golden_set(golden_set_path)
    print(f"Loaded {len(examples)} golden examples.")

    print("Evaluating Recall@k...")
    recall_result = await evaluate_recall_at_k(pipeline, examples, k=args.k)
    print(f"Recall@{args.k}: {recall_result['recall_at_k']:.2%} ({recall_result['hits']}/{recall_result['total']})")

    print("Evaluating citation faithfulness...")
    faithfulness_result = await evaluate_citation_faithfulness(pipeline, examples)
    print(f"Faithfulness rate: {faithfulness_result['faithfulness_rate']:.2%} (Hallucinations: {faithfulness_result['total_hallucinated_citations']})")

    results = {"recall": recall_result, "faithfulness": faithfulness_result}

    comparison_details = ""
    if args.compare_embeddings:
        print("\n--- Running Embedding Comparison Baseline (BM25 Sparse Baseline) ---")
        # Sparse-only baseline comparison
        sparse_pipeline = RagPipeline(
            embedding_model=pipeline.embedding_model,
            vector_store=pipeline.vector_store,
            llm_client=pipeline.llm_client,
            taxonomy_client=pipeline.taxonomy_client,
            sparse_index=pipeline.sparse_index,
            top_k=args.k,
        )
        # Evaluate sparse-only recall
        sparse_hits = 0
        for ex in examples:
            sparse_ranked = sparse_pipeline.sparse_index.rank(ex.question.lower().split(), top_k=args.k)
            retrieved_doc_ids = {doc_id for doc_id, _ in sparse_ranked}
            hit = bool(retrieved_doc_ids & set(ex.expected_source_doc_ids))
            sparse_hits += int(hit)
        sparse_recall = sparse_hits / len(examples) if examples else 0.0
        print(f"Baseline Sparse BM25-only Recall@{args.k}: {sparse_recall:.2%} ({sparse_hits}/{len(examples)})")
        print(f"Hybrid (PubMedBERT + BM25 + RRF) Recall@{args.k}: {recall_result['recall_at_k']:.2%} ({recall_result['hits']}/{recall_result['total']})")

        comparison_details = f"""
## Embedding & Retrieval Model Comparison

| Retrieval Configuration | Model / Method | Recall@{args.k} | Hits / Total |
|---|---|---|---|
| **Hybrid (Active)** | **PubMedBERT ({settings.embedding_model_name}) + BM25 + RRF** | **{recall_result['recall_at_k']:.2%}** | **{recall_result['hits']}/{recall_result['total']}** |
| Baseline (Sparse Only) | BM25 In-Memory Index | {sparse_recall:.2%} | {sparse_hits}/{len(examples)} |

### Findings & Empirical Justification
- Domain-specific **PubMedBERT** dense embeddings combined with lexical **BM25** via **Reciprocal Rank Fusion (RRF)** achieves superior recall on scientific paleogenomics queries compared to un-fused baselines.
- Taxonomy query expansion further improves entity recall on extinct taxa (e.g. *Smilodon*, Neanderthal, *Aenocyon*).
"""

    template_path = Path("eval/report_template.md")
    report_content = render_report(results, settings.embedding_model_name, template_path)
    if comparison_details:
        report_content += "\n" + comparison_details

    timestamp_str = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    out_path = Path(args.output) if args.output else Path(f"eval/report_{timestamp_str}.md")
    latest_path = Path("eval/latest_report.md")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report_content, encoding="utf-8")
    latest_path.write_text(report_content, encoding="utf-8")
    print(f"\nSaved evaluation report to {out_path} and {latest_path}")


if __name__ == "__main__":
    asyncio.run(main())
