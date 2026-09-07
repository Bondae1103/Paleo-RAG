# DECISIONS.md

Architectural Decision Records (ADR) and empirical justifications for PaleoRAG.

## 1. Sparse Retrieval Backend: `rank_bm25` (In-Process) with Auto-Sync

**Chosen:** `rank_bm25` (`BM25SparseIndex` in `backend/core/rag_pipeline.py`).

**Why:** Qdrant's native sparse vector support requires additional collection configuration and specialized sparse embedding encoders. `rank_bm25` provides BM25Okapi lexical matching with zero extra infrastructure and is synchronized from the vector store (`BM25SparseIndex.sync_from_vector_store()`). It seamlessly integrates into `VectorStore.hybrid_search()` via Reciprocal Rank Fusion (RRF, $k=60$).

**Empirical Result:** Combined with PubMedBERT dense vectors, hybrid search achieved 100.00% Recall@5 on the 27-question golden paleogenomics benchmark.

---

## 2. Cross-Encoder Reranker: `cross-encoder/ms-marco-MiniLM-L-6-v2`

**Chosen:** Implemented in `backend/core/rag_pipeline.py` and configurable via `RERANKER_ENABLED` and `RERANKER_MODEL_NAME` in `backend/config.py`.

**Why:** Allows high-precision second-stage reranking over top candidates ($k \times 3$) prior to truncation to `top_k`. Implemented with `sentence_transformers.CrossEncoder` with lazy loading and graceful fallback.

---

## 3. Point ID Scheme in Qdrant: UUID5-Derived from `{doc_id}::{chunk_index}`

**Chosen:** `_to_qdrant_point_id()` in `backend/core/vector_store.py` deterministically maps the natural human-readable ID (`"doc123::4"`) to a UUID5 using a fixed namespace.

**Why:** Qdrant requires point IDs to be either unsigned integers or valid UUID strings (arbitrary strings are rejected). UUID5 was chosen because it is a deterministic hash of the input string: the same `doc_id`/`chunk_index` pair always produces the exact same point ID across re-ingestion passes, guaranteeing idempotent deduplication, in-place updates, and deletions. The human-readable ID is preserved in the chunk payload.

---

## 4. Ingestion & Document Parsing: JATS XML & Layout-Aware PDF

**Chosen:**
- **PMC OA**: NCBI E-utilities (ESearch, ESummary, EFetch) fetching full JATS XML, parsed into semantic sections (Abstract, Methods, Results, Discussion, Table, Caption) via `parse_jats_xml()` in `backend/utils/pdf_parser.py`.
- **bioRxiv**: Direct PDF download (`https://www.biorxiv.org/content/{doi}.full.pdf`) parsed via PyMuPDF (`fitz`) with font-size and bold-header heuristics, atomic table detection, and caption prefix grouping (`parse_pdf()`).
- **License Enforcement**: Strict filtering to approved open-access licenses (`cc0`, `cc-by`, `cc-by-sa`, `cc-by-nc`).

---

## 5. Taxonomy Query Expansion: GBIF & Paleobiology Database (PBDB)

**Chosen:** `TaxonomyClient` in `backend/utils/taxonomy_client.py` performs n-gram entity extraction from queries, matching against GBIF Backbone Taxonomy with fallback to Paleobiology Database (PBDB) for extinct prehistoric taxa, cached with 30-day TTL.

**Why:** Scientific literature on paleogenomics often uses formal Latin binomen (e.g. *Smilodon fatalis*, *Aenocyon dirus*, *Mammuthus primigenius*) whereas user queries frequently use vernacular terms ("saber-tooth cat", "dire wolf", "woolly mammoth"). Dynamic expansion bridges lexical and semantic gaps without requiring retraining.

---

## 6. Real Evaluation Harness & Golden Benchmark

**Chosen:** `eval/run_eval.py` executed against `eval/golden_set.jsonl` (27 peer-reviewed paleogenomics and evolutionary biology questions referencing ingested documents in `data/processed/manifest.jsonl`).

**Benchmark Results:**
- **Recall@5**: **100.00%** (27/27)
- **Citation Faithfulness**: **100.00%** (0 hallucinated markers across all generated answers)
- **Report**: Stored in `eval/latest_report.md`.

