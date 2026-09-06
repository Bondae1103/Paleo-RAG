# PaleoRAG Evaluation Report

**Generated:** {timestamp}
**Embedding model:** {embedding_model_name}

## Retrieval

- Recall@{k}: **{recall_at_k}**
- Golden set size: {total_questions} questions

## Citation faithfulness

- Faithfulness rate (answers with zero hallucinated citations): **{faithfulness_rate}**
- Total hallucinated citation markers detected: {total_hallucinated_citations}

## Notes

- A hallucinated citation is any inline `[doc_id:chunk_index]` marker in a generated
  answer that does not correspond to a chunk actually retrieved for that query.
- Recall@k counts a hit if *any* expected source doc_id appears among the top-k
  retrieved chunks' doc_ids for that question.
- If comparing embedding models, run this report once per model and diff the
  Recall@k numbers directly — see `run_eval.py --compare-embeddings`.
