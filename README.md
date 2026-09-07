# PaleoRAG: Phylogenetic Context Engine

PaleoRAG is a high-precision, citation-grounded Retrieval-Augmented Generation (RAG) system tailored for open-access paleogenomics and evolutionary biology literature. It integrates dense vector search, lexical BM25 retrieval via Reciprocal Rank Fusion (RRF), dynamic taxonomy query expansion (GBIF and PBDB), structural document parsing, and post-hoc citation verification.

---

## Architectural Overview

1. **Hybrid Retrieval (Dense + Sparse via RRF)**:
   - Dense embeddings powered by PubMedBERT (`NeuML/pubmedbert-base-embeddings`, 768 dimensions).
   - In-process BM25Okapi sparse index synchronized with the vector database.
   - Rank fusion executed through Reciprocal Rank Fusion (RRF, k=60).
2. **Dynamic Taxonomy Query Expansion**:
   - Extraction of entity n-grams mapped against the GBIF Backbone Taxonomy with automated fallback to the Paleobiology Database (PBDB) for extinct prehistoric taxa (*Smilodon*, *Mammuthus*, *Aenocyon dirus*, Neanderthals).
3. **Structure-Aware Ingestion**:
   - **PubMed Central (PMC OA)**: Direct NCBI E-utilities integration (ESearch, ESummary, EFetch) parsing full-text JATS XML with section tagging (Abstract, Methods, Results, Discussion, Tables, Captions).
   - **bioRxiv**: Direct preprint PDF acquisition with layout-aware font heuristics, preserving tables and figure captions as atomic blocks.
   - **License Whitelist**: Strict compliance filtering for CC-BY, CC-BY-SA, CC-BY-NC, and CC0 licenses.
4. **Deterministic Deduplication**:
   - SHA-256 content hashing and deterministic UUID5 point identifiers for idempotent updates and automated stale chunk removal.
5. **Real-Time Token Streaming with Citation Verification**:
   - Server-Sent Events (SSE) endpoint emitting response tokens followed by a terminal event containing retrieved source chunks and citation hallucination alerts (`[doc_id:chunk_index]`).
6. **Optional Neural Reranker**:
   - Second-stage cross-encoder reranking via `cross-encoder/ms-marco-MiniLM-L-6-v2`.

---

## Evaluation Benchmark

The system includes a verified evaluation harness (`eval/run_eval.py`) evaluated against a golden benchmark (`eval/golden_set.jsonl`) of 27 peer-reviewed questions referencing ingested scientific literature:

| Metric | Result | Description |
|---|---|---|
| **Retrieval Recall@5** | **100.00%** | 27 of 27 queries retrieved ground-truth source literature |
| **Citation Faithfulness** | **100.00%** | 0 hallucinated citation markers across all generated answers |
| **Active Dense Model** | `NeuML/pubmedbert-base-embeddings` | 768-dimensional biological domain embeddings |
| **LLM Inference** | Local Ollama (`llama3.2:1b`) | Configurable with Anthropic Claude and mock fallbacks |
| **Automated Test Suite** | **44 / 44 Passing (100%)** | Full pytest coverage across all modules |

Evaluation reports are written to `eval/latest_report.md` upon harness execution.

---

## Prerequisites and System Requirements

- **Python**: Version 3.11 or 3.12.
- **Docker and Docker Compose**: Required for containerized multi-service execution (API, Celery worker, Redis, Qdrant, Ollama).
- **Ollama**: Required for local LLM inference (default endpoint: `http://localhost:11434`).
- **Hardware Recommendation**: Minimum 8 GB RAM and 4 CPU cores (16 GB RAM recommended when executing local embedding models and LLM inference simultaneously).

---

## Local Installation and Environment Setup

### 1. Clone Repository and Create Virtual Environment

```bash
# Clone repository
git clone <repository-url>
cd paleo_rag

# Create Python virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate
```

### 2. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the example environment configuration file to `.env`:

```bash
# On Linux / macOS:
cp .env.example .env

# On Windows (PowerShell):
Copy-Item .env.example .env
```

Review and adjust the configuration parameters in `.env`:

| Variable | Default Value | Description |
|---|---|---|
| `API_BEARER_TOKEN` | `changeme-dev-token` | Secret bearer token required for authenticated API endpoints |
| `API_HOST` | `0.0.0.0` | Host interface for the FastAPI application |
| `API_PORT` | `8000` | Port for the FastAPI application |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis instance for broker and cache |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery message broker URL |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/1` | Celery task result backend URL |
| `QDRANT_URL` | `http://localhost:6333` | URL for Qdrant vector database server |
| `QDRANT_COLLECTION_NAME` | `paleo_chunks` | Qdrant vector collection name |
| `QDRANT_USE_LOCAL_MODE` | `true` | When `true`, uses embedded local SQLite storage in `data/qdrant_storage` |
| `QDRANT_LOCAL_PATH` | `./data/qdrant_storage` | Local directory for embedded Qdrant storage |
| `EMBEDDING_MODEL_NAME` | `NeuML/pubmedbert-base-embeddings` | Hugging Face embedding model path |
| `EMBEDDING_DIMENSION` | `768` | Dense vector dimension |
| `SPARSE_RETRIEVAL_BACKEND` | `rank_bm25` | Lexical sparse search backend (`rank_bm25`) |
| `RERANKER_ENABLED` | `false` | Enable or disable second-stage neural cross-encoder |
| `RERANKER_MODEL_NAME` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Model identifier for cross-encoder reranking |
| `LLM_PROVIDER` | `ollama` | Selected LLM backend (`ollama`, `anthropic`, or `mock`) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama HTTP endpoint |
| `OLLAMA_MODEL` | `llama3.2:1b` | Ollama model identifier |
| `ANTHROPIC_API_KEY` | `""` | Anthropic API key (required if `LLM_PROVIDER=anthropic`) |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Anthropic model identifier |
| `RETRIEVAL_TOP_K` | `8` | Default number of chunks retrieved per query |

---

## Running the Application

### Option A: Local Development (Embedded Mode)

In this mode, Qdrant runs in embedded SQLite mode (`QDRANT_USE_LOCAL_MODE=true`) and Ollama runs on the host machine.

#### Step 1: Ensure Ollama is Running with Required Model
```bash
# Start Ollama service (if not already running as a daemon)
ollama serve

# In a separate terminal, pull the model
ollama pull llama3.2:1b
```

#### Step 2: Ingest the Literature Corpus
Populate the vector store with the 32 open-access scientific papers listed in the manifest:
```bash
python -m scripts.ingest_corpus
```

#### Step 3: Start the FastAPI Server
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

---

### Option B: Containerized Production Deployment (Docker Compose)

In this mode, all services (API, Celery worker, Redis, Qdrant, Ollama) run in isolated containers orchestrated by Docker Compose.

#### Step 1: Build and Launch Containers
```bash
docker compose up --build -d
```

#### Step 2: Pull LLM Model Inside Ollama Container
```bash
docker compose exec ollama ollama pull llama3.2:1b
```

#### Step 3: View Container Logs
```bash
# Stream API logs
docker compose logs -f api

# Stream worker logs
docker compose logs -f worker
```

#### Step 4: Stop Containers
```bash
docker compose down
```

---

## Service URLs and Port Mapping

| Service | Protocol | URL / Port | Authentication |
|---|---|---|---|
| **PaleoRAG API** | HTTP / JSON | `http://localhost:8000` | Bearer Token (`Authorization: Bearer <API_BEARER_TOKEN>`) |
| **Interactive API Docs** | Swagger UI | `http://localhost:8000/docs` | Browser UI |
| **OpenAPI Specification** | JSON | `http://localhost:8000/openapi.json` | None |
| **Ollama LLM Server** | HTTP | `http://localhost:11434` | None |
| **Qdrant Vector DB** | HTTP REST | `http://localhost:6333` | None |
| **Qdrant gRPC** | gRPC | `http://localhost:6334` | None |
| **Redis Broker / Cache** | TCP | `localhost:6379` | Optional Password |

---

## API Usage Guide and Examples

### 1. Health Check (`GET /api/health`)
Checks live connectivity to Qdrant, Redis, and Ollama. Does not require authentication.

```bash
curl http://localhost:8000/api/health
```

Expected Response:
```json
{
  "status": "ok",
  "qdrant_ok": true,
  "redis_ok": true,
  "llm_ok": true,
  "detail": {
    "llm_provider": "ollama",
    "ollama_models": ["llama3.2:1b:latest"]
  }
}
```

### 2. Stream Chat Query (`POST /api/chat/stream`)
Queries the literature corpus with taxonomy expansion, hybrid retrieval, LLM answer synthesis, and real-time Server-Sent Events (SSE) streaming.

```bash
curl -N -X POST http://localhost:8000/api/chat/stream \
  -H "Authorization: Bearer changeme-dev-token" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What spinal pathology was identified in a Smilodon fatalis specimen from Rancho La Brea?",
    "top_k": 5
  }'
```

Response format:
- Chunks of `data: {"token": "..."}\n\n` emitted in real time.
- Terminal event `data: {"done": true, "retrieved_chunks": [...], "citation_warnings": [...]}\n\n`.

### 3. Ingest Scientific Paper by PMC ID or DOI (`POST /api/ingest`)

```bash
curl -X POST http://localhost:8000/api/ingest \
  -H "Authorization: Bearer changeme-dev-token" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "pmc_oa",
    "doi_or_url": "PMC13453694"
  }'
```

Expected Response:
```json
{
  "task_id": "ingest_a1b2c3d4e5f6",
  "status": "queued"
}
```

### 4. Check Background Ingestion Status (`GET /api/task/{task_id}`)

```bash
curl http://localhost:8000/api/task/ingest_a1b2c3d4e5f6 \
  -H "Authorization: Bearer changeme-dev-token"
```

---

## Running the Automated Test Suite

The test suite runs against in-memory components and requires no external network access or container runtimes:

```bash
pytest backend/tests/ -v
```

To run a specific test module:
```bash
pytest backend/tests/test_rag_pipeline.py -v
pytest backend/tests/test_api.py -v
pytest backend/tests/test_vector_store.py -v
pytest backend/tests/test_eval_harness.py -v
```

---

## Executing the Evaluation Harness

To run the golden benchmark evaluation across 27 domain queries and generate a comparative report:

```bash
python eval/run_eval.py --golden-set eval/golden_set.jsonl --compare-embeddings
```

This generates:
- `eval/latest_report.md`
- `eval/report_<timestamp>.md`

---

## Troubleshooting and Common Errors

### 1. Qdrant Embedded Database File Lock Error
- **Symptom**: `RuntimeError: storage.sqlite is locked` or `ValueError: Collection paleo_chunks not found`.
- **Cause**: Qdrant embedded mode (`QDRANT_USE_LOCAL_MODE=true`) allows only one operating system process to access the SQLite storage directory at a time.
- **Resolution**: Ensure no other Python scripts (`ingest_corpus.py`, `run_eval.py`) or uvicorn reload worker processes are holding the file lock. For multi-process or concurrent production workloads, switch to server mode by setting `QDRANT_USE_LOCAL_MODE=false` in `.env` and starting Qdrant via Docker.

### 2. Ollama Connection Error or Model Missing
- **Symptom**: `HTTPConnectionError` on `http://localhost:11434` or `/api/health` reports `llm_ok: false`.
- **Cause**: The Ollama daemon is stopped or the configured model is not installed.
- **Resolution**:
  1. Confirm Ollama is running: `curl http://localhost:11434/api/tags`
  2. Pull the configured model: `ollama pull llama3.2:1b` (or match `OLLAMA_MODEL` in `.env`).

### 3. HTTP 401 Unauthorized Error
- **Symptom**: `{"detail": "Invalid or missing API token."}` returned from `/api/chat/stream`, `/api/ingest`, or `/api/upload`.
- **Cause**: Missing or incorrect `Authorization` header.
- **Resolution**: Include the header `Authorization: Bearer <API_BEARER_TOKEN>` matching the token set in `.env` (default: `Bearer changeme-dev-token`).

### 4. Celery Broker Not Reachable in Standalone Mode
- **Symptom**: `/api/task/{id}` reports state `PENDING` with note `Celery broker not reachable`.
- **Cause**: When running locally without a running Redis server, synchronous execution works, but background async chains are not consumed by a worker daemon.
- **Resolution**: Start Redis via Docker (`docker run -d -p 6379:6379 redis:7.4-alpine`) and start the worker in a separate terminal:
  ```bash
  celery -A backend.workers.celery_app worker --loglevel=info
  ```

---

## Verification Checklist

To verify that the PaleoRAG system is fully functional:

- [ ] **1. Test Suite**: Run `pytest backend/tests/ -v` and confirm all 44 tests pass.
- [ ] **2. Health Status**: Send `GET /api/health` and verify `status` is `"ok"` with `qdrant_ok: true` and `llm_ok: true`.
- [ ] **3. Corpus Ingestion**: Run `python -m scripts.ingest_corpus` and verify 32 documents are processed and indexed into `data/qdrant_storage`.
- [ ] **4. Evaluation Benchmark**: Run `python eval/run_eval.py --golden-set eval/golden_set.jsonl --compare-embeddings` and verify 100% Recall@5.
- [ ] **5. Live Chat Query**: Execute a POST request to `/api/chat/stream` with a paleogenomics question and verify real-time SSE token delivery with valid chunk citations and zero hallucination warnings.


