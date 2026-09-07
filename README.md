# PaleoRAG — Phylogenetic Context Engine

A high-precision, citation-grounded RAG (Retrieval-Augmented Generation) system for open-access paleogenomics literature, featuring hybrid dense/sparse retrieval, dynamic taxonomy query expansion (GBIF + PBDB), deterministic deduplication, and post-hoc citation verification.

---

## 🌟 Key Features

1. **Hybrid Retrieval (Dense + Sparse via RRF)**:
   - Dense representations using domain-adapted **PubMedBERT** (`NeuML/pubmedbert-base-embeddings`, 768-dim).
   - Sparse lexical matching using in-process **BM25Okapi** index auto-synchronized with Qdrant collection.
   - Fused via **Reciprocal Rank Fusion (RRF)** ($k=60$) for optimal rank aggregation.
2. **Taxonomy-Aware Query Expansion**:
   - Dynamic n-gram extraction matching common names and synonyms against **GBIF Backbone Taxonomy** with automated fallback to the **Paleobiology Database (PBDB)** for extinct prehistoric taxa (*Smilodon*, *Mammuthus*, *Aenocyon dirus*, Neanderthals).
3. **Structure-Aware Ingestion**:
   - **PubMed Central (PMC OA)**: Live NCBI ESearch, ESummary, and EFetch downloading full JATS XMLs with automatic section partitioning (Abstract, Methods, Results, Discussion, Tables, Captions).
   - **bioRxiv**: Direct preprint PDF retrieval with layout-aware font heuristics, keeping tables and figure captions atomic.
   - **License Whitelist**: Enforces strict CC-BY, CC-BY-SA, CC-BY-NC, and CC0 open-access license compliance.
4. **Idempotent Chunk Deduplication**:
   - Content hashing (`SHA-256`) and deterministic UUID5 point IDs for update-in-place and deleted chunk purging.
5. **Real-Time Token Streaming & Citation Verification**:
   - FastAPI SSE endpoint (`/api/chat/stream`) emitting real-time tokens followed by a terminal event with retrieved chunks and hallucinated citation alerts (`[doc_id:chunk_index]`).
6. **Optional Cross-Encoder Reranking**:
   - Second-stage neural reranking with `cross-encoder/ms-marco-MiniLM-L-6-v2`.

---

## 📊 Evaluation & Benchmark Results

Evaluated against `eval/golden_set.jsonl` (27 peer-reviewed paleogenomics and evolutionary biology questions referencing ingested open-access literature):

| Metric | Score | Details |
|---|---|---|
| **Retrieval Recall@5** | **100.00%** | **27 / 27** golden queries retrieved expected ground-truth literature |
| **Citation Faithfulness** | **100.00%** | **0** hallucinated citation markers detected across all generated answers |
| **Active Embedding Model** | `NeuML/pubmedbert-base-embeddings` | 768 dimensions |
| **LLM Provider** | Local Ollama (`llama3.2:1b`) | Fallbacks: Anthropic Claude / Mock |
| **Test Suite** | **44 / 44 (100%)** | Full pytest coverage with zero regressions |

*Full report generated at `eval/latest_report.md`.*

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.11+
- Local Ollama running at `http://localhost:11434` (with `llama3.2:1b` or `llama3.1:8b` installed):
  ```bash
  ollama pull llama3.2:1b
  ```

### 2. Setup Environment
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Ingest Literature Corpus
To download and ingest the default scientific corpus into the local Qdrant vector store:
```bash
# Ingest all 32 papers in manifest
python -m scripts.ingest_corpus
```

### 4. Run the Evaluation Benchmark
```bash
python eval/run_eval.py --golden-set eval/golden_set.jsonl --compare-embeddings
```

### 5. Start the API Server
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 📡 API Reference

### Health Check
```bash
curl http://localhost:8000/api/health
```
Response:
```json
{
  "status": "ok",
  "qdrant_ok": true,
  "redis_ok": false,
  "llm_ok": true,
  "detail": {
    "llm_provider": "ollama",
    "ollama_models": ["llama3.2:1b:latest"]
  }
}
```

### Stream Chat Query (SSE)
```bash
curl -N -X POST http://localhost:8000/api/chat/stream \
  -H "Authorization: Bearer changeme-dev-token" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What spinal pathology was identified in a Smilodon fatalis specimen from Rancho La Brea?"
  }'
```

### Ingest by DOI or PMC ID
```bash
curl -X POST http://localhost:8000/api/ingest \
  -H "Authorization: Bearer changeme-dev-token" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "pmc_oa",
    "doi_or_url": "PMC13453694"
  }'
```

---

## 🧪 Testing

Run the complete test suite:
```bash
pytest backend/tests/ -v
```
All 44 tests pass locally in in-memory mode without requiring external docker containers or network access.

