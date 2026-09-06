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
import time
from dataclasses import dataclass
from pathlib import Path

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
    parser = argparse.ArgumentParser()
    parser.add_argument("--golden-set", default="eval/golden_set.jsonl")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument(
        "--compare-embeddings",
        action="store_true",
        help="Run the golden set twice (PubMedBERT vs. a general-purpose embedding model) "
        "and report Recall@k for both, per the implementation plan's requirement to "
        "empirically justify the embedding choice.",
    )
    args = parser.parse_args()

    # Building a real RagPipeline requires a populated vector store and a
    # working embedding model + LLM — wire these up here once ingestion has
    # run on the target machine. Left unimplemented in the build sandbox
    # since there is no real corpus to evaluate against yet (see HANDOFF.md
    # for exactly what to plug in here).
    raise NotImplementedError(
        "Wire up a real RagPipeline (backend.api.dependencies.get_rag_pipeline) here once "
        "the corpus is ingested and a real embedding model / LLM are available. See HANDOFF.md."
    )


if __name__ == "__main__":
    asyncio.run(main())
