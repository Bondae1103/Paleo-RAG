# AGENT BUILD PROMPT: Phylogenetic Context Engine (PaleoRAG)

You are an autonomous coding agent tasked with building a production-quality Retrieval-Augmented Generation (RAG) system for paleogenomics literature search, called **PaleoRAG**. Follow this specification exactly. Where a decision is not specified, choose the option that favors correctness, reproducibility, and low operating cost, and document the choice in `DECISIONS.md`.

Work in phases, in order. Do not skip ahead to a later phase until the current phase's acceptance criteria pass. After each phase, run the specified tests and print a short status report before continuing.

---

## 0. Non-negotiable constraints

- **Legal data sourcing only.** Never ingest paywalled full text. Only use: PubMed Central Open Access subset, bioRxiv/biorxiv preprints, PLOS journals, and the Paleobiology Database (PBDB) API. If a source's license is unclear, store metadata only (title, abstract, DOI, link) and exclude full text.
- **Local-first, cost-aware.** Default to local models (Ollama) and self-hosted infra (Docker Compose). Cloud LLM APIs are opt-in via config, never required to run the system.
- **Everything must be testable.** Every module gets at least one unit test. The retrieval pipeline gets an evaluation harness (Phase 6) — this is not optional and not deferred to "later."
- **Reproducibility.** Pin all dependency versions. `docker-compose up` must bring the full stack up from a clean clone with no manual steps beyond `.env` population.

---

## 1. Repository structure

Create exactly this structure:

```
paleo_rag/
├── docker-compose.yml
├── README.md
├── DECISIONS.md
├── requirements.txt
├── .env.example
├── data/
│   ├── raw_pdfs/
│   ├── processed/
│   └── qdrant_storage/
├── eval/
│   ├── golden_set.jsonl
│   ├── run_eval.py
│   └── report_template.md
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   ├── routes.py
│   │   ├── schemas.py
│   │   └── dependencies.py
│   ├── core/
│   │   ├── rag_pipeline.py
│   │   ├── embeddings.py
│   │   ├── vector_store.py
│   │   ├── chunking.py
│   │   ├── query_expansion.py
│   │   └── llm_client.py
│   ├── workers/
│   │   ├── celery_app.py
│   │   └── tasks.py
│   ├── utils/
│   │   ├── pdf_parser.py
│   │   ├── taxonomy_client.py
│   │   ├── dedup.py
│   │   └── logging_config.py
│   └── tests/
│       ├── test_chunking.py
│       ├── test_taxonomy_client.py
│       ├── test_vector_store.py
│       └── test_api.py
└── frontend/
    └── (placeholder — out of scope for this build)
```

---

## 2. Tech stack (pinned)

| Component | Choice | Version pin |
|---|---|---|
| API framework | FastAPI | `fastapi==0.115.*`, `uvicorn[standard]==0.32.*` |
| Task queue | Celery + Redis | `celery==5.4.*`, `redis==5.1.*` |
| Vector DB | Qdrant (Docker) | `qdrant-client==1.12.*`, image `qdrant/qdrant:v1.12.1` |
| Dense embeddings | `NeuML/pubmedbert-base-embeddings` (sentence-transformers compatible) | via `sentence-transformers==3.2.*` |
| Sparse retrieval | BM25 via Qdrant's built-in sparse vector support (`Qdrant FastEmbed BM25`) or `rank_bm25==0.2.*` if not using Qdrant sparse vectors | pick one, document in DECISIONS.md |
| PDF parsing | PyMuPDF (`fitz`) | `pymupdf==1.24.*` |
| LLM (local) | Ollama running `llama3.1:8b` | Ollama server, not pip-installed |
| LLM (optional cloud) | Anthropic API, `claude-sonnet-4-6` | `anthropic==0.39.*` |
| Taxonomy | GBIF Species API + Paleobiology Database API | `httpx==0.27.*` for calls |
| Validation | Pydantic v2 | `pydantic==2.9.*` |
| Testing | pytest | `pytest==8.3.*` |

**Do not build a custom taxonomy lookup table.** Use:
- GBIF Species Match API: `https://api.gbif.org/v1/species/match?name={common_or_scientific_name}`
- PBDB taxa API: `https://paleobiodb.org/data1.2/taxa/list.json?name={name}`

Cache all taxonomy lookups in Redis with a 30-day TTL to avoid re-hitting external APIs.

---

## 3. Phase 1 — Data ingestion sources (build first, before any RAG logic)

Implement three ingestion connectors in `backend/utils/`:

1. **`pmc_oa_connector.py`** — pulls from PMC OA Web Service (`https://www.ncbi.nlm.nih.gov/pmc/tools/oa-service/`). Filter by search terms: `"ancient DNA"`, `"paleogenomics"`, `"paleogenetics"`, `"sedaDNA"`, plus any taxon names the user supplies.
2. **`biorxiv_connector.py`** — uses bioRxiv's public API (`https://api.biorxiv.org/`) filtered to the "Genomics" and "Evolutionary Biology" collections, license field must be CC-BY or CC-BY-NC.
3. **`pbdb_connector.py`** — pulls structured occurrence/taxonomy data (not free text) from PBDB, stored separately as structured metadata, not chunked into the RAG corpus, but joinable by taxon name for query-time filtering (see Phase 4, payload filtering).

Each connector must:
- Respect rate limits (add `time.sleep` per API's documented limits; PMC and bioRxiv are ~3 req/sec max).
- Write a manifest row per document to `data/processed/manifest.jsonl` with: `doc_id`, `source`, `license`, `doi`, `title`, `retrieved_at`, `raw_path`.
- Skip and log (not crash) on any document with an ambiguous or missing license.

**Acceptance criteria:** running `python -m backend.utils.pmc_oa_connector --query "ancient DNA" --limit 20` produces 20 PDFs/XML in `data/raw_pdfs/` and 20 manifest rows, with zero paywalled documents.

---

## 4. Phase 2 — Parsing & chunking

**`pdf_parser.py`**: Use PyMuPDF to extract text with layout info preserved (block-level, not just raw text dump). Extract:
- Section headers (detect via font size and bold flags, not regex on "Abstract"/"Introduction" alone — journal templates vary)
- Tables as separate structured blocks (do not merge into flowing text — an allele frequency table sliced mid-row is useless)
- Figure captions as their own chunk type, tagged `chunk_type: "caption"`

**`chunking.py`**: Implement **structure-aware chunking**, not naive fixed-size splitting:
1. First split by detected section (Abstract, Introduction, Methods, Results, Discussion, References — References excluded from ingestion).
2. Within a section, split further only if the section exceeds 512 tokens, using a recursive character splitter with a 50-token overlap.
3. Never split a detected table or figure caption across chunks — keep as one atomic chunk even if it exceeds the token target, up to a hard cap of 1024 tokens (truncate with a `"[TRUNCATED]"` marker beyond that, logged for review).
4. Every chunk gets metadata: `doc_id`, `section`, `chunk_type` (`text`|`table`|`caption`), `page_number`, `chunk_index`.

**Deduplication (`dedup.py`)**: Before embedding, hash each chunk's normalized text (lowercase, whitespace-collapsed) with SHA-256. On re-ingestion of an updated paper version (same DOI, newer retrieved_at), diff chunk hashes against the existing set for that `doc_id` and only re-embed changed/new chunks; delete stale chunk IDs from Qdrant.

**Acceptance criteria:** unit test `test_chunking.py` asserts that a synthetic 3-table, 2-section fixture PDF produces chunks where no table's row count is split across two chunk objects.

---

## 5. Phase 3 — Embeddings & vector store

**`embeddings.py`**: Wrap `NeuML/pubmedbert-base-embeddings` behind an interface `EmbeddingModel.embed(texts: list[str]) -> list[list[float]]`. Make the model name configurable via `.env` (`EMBEDDING_MODEL_NAME`) so it can be swapped later without touching calling code — this is required, not optional, because PubMedBERT is trained on biomedical abstracts and may underperform on paleontological/geological vocabulary (taphonomy, stratigraphy). Log embedding latency per batch.

**`vector_store.py`**: Qdrant collection schema:

```python
collection_name = "paleo_chunks"
vector_config = {
    "dense": VectorParams(size=768, distance=Distance.COSINE),
}
sparse_vector_config = {
    "bm25": SparseVectorParams()  # if using Qdrant native sparse vectors
}
payload_schema = {
    "doc_id": "keyword",
    "doi": "keyword",
    "section": "keyword",
    "chunk_type": "keyword",
    "taxon_scientific_name": "keyword",   # populated via taxonomy_client at ingest time
    "taxon_common_names": "keyword[]",
    "geological_period": "keyword",        # from PBDB join, when available
    "publication_year": "integer",
    "chunk_text": "text",
}
```

Implement **hybrid search** as: dense cosine similarity + BM25 sparse score, combined via Reciprocal Rank Fusion (RRF), not a naive weighted sum (RRF is more robust to score-scale mismatches between dense and sparse).

Implement **payload filtering** as a first-class query parameter: allow filtering by `taxon_scientific_name`, `geological_period`, and `publication_year` range, combinable with the hybrid search (Qdrant `Filter` object passed alongside the query vector).

**Acceptance criteria:** `test_vector_store.py` inserts 5 synthetic chunks tagged with different taxa/years, then asserts a filtered query for `taxon_scientific_name="Smilodon fatalis"` + `publication_year >= 2015` returns only the matching subset regardless of semantic similarity ranking.

---

## 6. Phase 4 — Query expansion & taxonomy mapping

**`taxonomy_client.py`**: On query time, before embedding the user's query:
1. Extract candidate species/taxon mentions from the query (simple approach: named-entity check against a cached list of known taxa already ingested, plus a fallback call to GBIF match API for unrecognized terms).
2. Resolve common name → scientific binomial via GBIF; cross-check against PBDB for paleontological name validity (GBIF is extant-biased).
3. Expand the query to include both the common name and scientific name as search terms for the BM25 component (dense embedding uses the original query text unmodified, since embeddings already capture semantic similarity).
4. Cache resolution results in Redis (`taxon:{normalized_input}` → JSON, 30-day TTL).

**Acceptance criteria:** query `"saber-toothed cat gene flow"` resolves to include `"Smilodon"` in the expanded search terms, verified by `test_taxonomy_client.py` with GBIF calls mocked.

---

## 7. Phase 5 — Ingestion pipeline (Celery)

`tasks.py` defines one Celery task chain per document:

```
parse_document → chunk_document → dedup_check → embed_chunks → upsert_to_qdrant → update_manifest_status
```

Each step is its own Celery task (not one monolithic function) so failures are retryable at the granular level. Use Celery's `chain()` primitive. On failure, mark the manifest row `status: "failed"` with the exception message, do not silently drop the document.

`/api/upload` (FastAPI):
- Accepts a PDF file OR a DOI/URL to fetch.
- Validates license/source eligibility (reject if not from an approved source, per Section 0) before enqueueing.
- Returns `{"task_id": ..., "status": "queued"}` immediately.

`/api/task/{task_id}`: returns Celery task state (`PENDING`, `STARTED`, `SUCCESS`, `FAILURE`) plus, on failure, the error message.

**Acceptance criteria:** uploading a known-good PMC OA PDF results in searchable chunks in Qdrant within 60 seconds on a machine with a local embedding model warm-started.

---

## 8. Phase 6 — Evaluation harness (required, build before the chat endpoint is considered "done")

Create `eval/golden_set.jsonl`: minimum 25 hand-written question/answer pairs, each with:
```json
{"question": "...", "expected_source_doc_ids": ["..."], "expected_answer_contains": ["key fact 1", "key fact 2"]}
```

`eval/run_eval.py` computes and reports:
- **Retrieval Recall@5**: fraction of questions where at least one `expected_source_doc_ids` chunk appears in the top-5 retrieved.
- **Citation faithfulness**: for each generated answer, check whether every citation the LLM outputs corresponds to an actually-retrieved chunk (flag any hallucinated citation — a citation to a `doc_id` not in the retrieved set for that query).
- **Embedding model comparison**: run the full golden set twice — once with PubMedBERT, once with a general-purpose model (e.g., `BAAI/bge-base-en-v1.5`) — and report Recall@5 for both, to empirically justify the embedding choice rather than assume it.

Output a markdown report to `eval/report_<timestamp>.md` using `eval/report_template.md`.

**Acceptance criteria:** this phase is not complete until `run_eval.py` executes end-to-end and produces a report with real (not placeholder) numbers on the actual ingested corpus.

---

## 9. Phase 7 — Retrieval & generation API

`/api/chat/stream` (SSE via FastAPI `StreamingResponse`):
1. Accept `{"query": str, "filters": {...optional...}}`.
2. Run query expansion (Phase 4).
3. Run hybrid search with RRF (Phase 3), top-k=8, then re-rank the top 8 by cross-encoder if `RERANKER_ENABLED=true` in config (optional stretch goal — implement the config flag even if the reranker itself is stubbed initially).
4. Build a prompt template that:
   - Instructs the model to answer only from provided context.
   - Requires inline citation markers `[doc_id:chunk_index]` for every factual claim.
   - Explicitly instructs the model to say "the provided literature does not address this" rather than fabricate, when context is insufficient.
5. Call `llm_client.py`, which abstracts over Ollama (default) and Anthropic API (optional), selected via `.env` `LLM_PROVIDER=ollama|anthropic`.
6. Stream tokens back over SSE; after the stream completes, run a post-hoc citation check (cross-reference every `[doc_id:chunk_index]` marker against the actually-retrieved set) and append a `citation_warnings` field to the final SSE event if any citation doesn't match.

**Acceptance criteria:** a manual query against the ingested PMC OA corpus returns a streamed answer where every citation marker resolves to a real retrieved chunk, verified by `test_api.py`.

---

## 10. Phase 8 — Operational hardening

- Add API key auth (simple bearer token via `.env`, checked in `dependencies.py`) on `/api/upload` and `/api/chat/stream`.
- Add structured logging (`logging_config.py`, JSON logs) for: ingestion task lifecycle, query latency breakdown (expansion time / retrieval time / generation time), and citation warning counts.
- Add a `/api/health` endpoint checking Qdrant, Redis, and Ollama connectivity.
- Add `docker-compose.yml` services: `api`, `worker`, `redis`, `qdrant`, and (if not run separately) `ollama`. Include healthchecks for each.

---

## 11. Definition of done

The build is complete when:
1. `docker-compose up` from a clean clone, with `.env` populated from `.env.example`, brings up a working stack with no manual steps.
2. `python -m backend.utils.pmc_oa_connector --query "ancient DNA" --limit 20` successfully ingests real documents end-to-end into Qdrant.
3. `pytest backend/tests/` passes fully.
4. `python eval/run_eval.py` produces a real evaluation report with Recall@5 and citation-faithfulness numbers, including the PubMedBERT vs. general-embedding comparison.
5. A manual `/api/chat/stream` query about a real ingested topic (e.g., "what genetic evidence exists for Smilodon population decline") returns a cited, streamed answer with zero citation warnings.
6. `DECISIONS.md` documents every place this spec said "choose and document" (BM25 implementation choice, reranker default, etc.).

Do not report the project as complete if step 4 (evaluation) is skipped or contains placeholder numbers — this is the most common way this class of project fails to hold up under technical interview scrutiny.
