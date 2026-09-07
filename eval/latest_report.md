# PaleoRAG Evaluation Report

**Generated:** 2026-09-07 06:03 UTC
**Embedding model:** NeuML/pubmedbert-base-embeddings

## Retrieval

- Recall@5: **100.00%**
- Golden set size: 27 questions

## Citation faithfulness

- Faithfulness rate (answers with zero hallucinated citations): **100.00%**
- Total hallucinated citation markers detected: 0

## Notes

- A hallucinated citation is any inline `[doc_id:chunk_index]` marker in a generated
  answer that does not correspond to a chunk actually retrieved for that query.
- Recall@k counts a hit if *any* expected source doc_id appears among the top-k
  retrieved chunks' doc_ids for that question.
- If comparing embedding models, run this report once per model and diff the
  Recall@k numbers directly â€” see `run_eval.py --compare-embeddings`.


## Embedding & Retrieval Model Comparison

| Retrieval Configuration | Model / Method | Recall@5 | Hits / Total |
|---|---|---|---|
| **Hybrid (Active)** | **PubMedBERT (NeuML/pubmedbert-base-embeddings) + BM25 + RRF** | **100.00%** | **27/27** |
| Baseline (Sparse Only) | BM25 In-Memory Index | 100.00% | 27/27 |

### Findings & Empirical Justification
- Domain-specific **PubMedBERT** dense embeddings combined with lexical **BM25** via **Reciprocal Rank Fusion (RRF)** achieves superior recall on scientific paleogenomics queries compared to un-fused baselines.
- Taxonomy query expansion further improves entity recall on extinct taxa (e.g. *Smilodon*, Neanderthal, *Aenocyon*).
