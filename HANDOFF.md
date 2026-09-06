# HANDOFF.md — Instructions for the agent continuing this build

You are picking up a partially-built implementation of PaleoRAG (see
`paleo_rag_agent_implementation_plan.md` for the full original spec). This
document tells you exactly what's already done and tested, what's written
but unverified, and what's not started — in priority order. Read this fully
before writing any new code; several things below are already implemented
and just need verification, not rewriting.

## Why some things are unverified, not missing

The environment that built this repo had restricted network egress: it
could reach `pypi.org`, `github.com`, and a few package registries, but
**not** `huggingface.co`, `ncbi.nlm.nih.gov`, `api.biorxiv.org`,
`api.gbif.org`, `paleobiodb.org`, `api.anthropic.com`, or any Docker/Ollama
runtime. So the code for those integrations is written, structurally
complete, and follows each service's documented API — but has never made a
real network call or been executed against a live server. Your job is
mostly **verification and fixing rough edges**, not designing from scratch.

Run `pytest backend/tests/ -v` first. All 33 tests should pass with zero
network access and no Docker running — that's your baseline confirming
nothing here is broken before you start.

---

## Step 1 — Get the real embedding model working (do this first)

Currently `backend/core/embeddings.py` has `MockEmbeddingModel` (tested,
works) and `SentenceTransformerEmbeddingModel` (written, never run).

```bash
pip install -r requirements.txt   # sentence-transformers + torch are in there
python -c "
from backend.core.embeddings import SentenceTransformerEmbeddingModel
m = SentenceTransformerEmbeddingModel('NeuML/pubmedbert-base-embeddings')
vecs = m.embed(['ancient DNA extraction from permafrost samples'])
print(len(vecs[0]), m.dimension)
"
```

If `NeuML/pubmedbert-base-embeddings` fails to load or its actual output
dimension isn't 768, fix `EMBEDDING_DIMENSION` in `.env` to match — the
Qdrant collection's `vector_size` is read from this setting
(`backend/config.py`), so it must match the real model's output exactly or
`vector_store.py`'s `create_collection` call will silently create a
mismatched collection.

Then wire `get_embedding_model()` in `backend/api/dependencies.py` to
actually use it in production (it already does, by default — just confirm
it works instead of throwing on first call).

## Step 2 — Stand up the real infrastructure and verify Celery end-to-end

```bash
docker-compose up --build
```

Then verify the full ingestion chain actually runs (not just imports
cleanly):

```bash
curl -X POST http://localhost:8000/api/upload \
  -H "Authorization: Bearer $API_BEARER_TOKEN" \
  -F "file=@/path/to/a/real/open-access/pdf.pdf" \
  -F "source=manual_upload"
# -> {"task_id": "...", "status": "queued"}

curl http://localhost:8000/api/task/<task_id> \
  -H "Authorization: Bearer $API_BEARER_TOKEN"
# poll until state == SUCCESS or FAILURE
```

If it fails, the most likely break points (in order of likelihood):
1. `backend/workers/tasks.py` passing dataclass instances through Celery's
   JSON serializer — I convert to `.__dict__` before returning from each
   task specifically to avoid this, but double check `ChunkType` (an Enum)
   serializes/deserializes correctly across task boundaries.
2. `VectorStore`'s `qdrant_use_local_mode=false` path needs a real Qdrant
   server reachable at `QDRANT_URL` — confirm docker-compose's network
   makes `http://qdrant:6333` resolvable from the `worker` container.

## Step 3 — Get real LLM generation working

`backend/core/llm_client.py` has `OllamaLLMClient` and `AnthropicLLMClient`,
both written against their documented streaming APIs, never executed.

```bash
docker exec -it paleo_rag-ollama-1 ollama pull llama3.1:8b
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Authorization: Bearer $API_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "test question"}'
```

If Ollama's `/api/generate` streaming response shape doesn't match what
`OllamaLLMClient.stream()` expects (I followed Ollama's documented NDJSON
format with a `response` field per line and a `done: true` terminal line —
verify this is still accurate for whatever Ollama version you pull), fix
the parsing there.

## Step 4 — Fix the ingestion connectors' unverified pieces

All three connectors (`pmc_oa_connector.py`, `biorxiv_connector.py`,
`pbdb_connector.py`) need a real run against their live APIs. Specific known
gaps, already flagged with comments in the code:

- **`pmc_oa_connector.py`**: the OA service returns XML, not JSON — the
  code currently stores `raw_xml` and hardcodes `license_tag = "cc-by"` as a
  placeholder (see `DECISIONS.md`). You need to actually parse the OA
  service's XML response (`xml.etree.ElementTree` is fine) to extract the
  real license and DOI fields, and gate ingestion on the real license value
  per Section 0 of the spec — do not skip this; a paywalled/unclear-license
  document slipping through is exactly what the spec's hard constraint
  exists to prevent.
- **`biorxiv_connector.py`**: the date range in `fetch_recent_details` is
  hardcoded to `2024-01-01/2024-12-31` — change this to a rolling window or
  make it a CLI argument.
- **`pbdb_connector.py`**: untested against live responses; the response
  field names (`early_interval`, `oei`, `rnk_name`) were taken from PBDB's
  documented schema but field availability can vary by taxon rank — verify
  against a few real taxa (e.g., `Smilodon`, `Mammuthus`) before trusting
  the geological-period join at ingest time.

Run each connector standalone first, inspect its manifest output, before
wiring into the full ingestion chain:

```bash
python -m backend.utils.pmc_oa_connector --query "ancient DNA" --limit 5
cat data/processed/manifest.jsonl
```

## Step 5 — Expand the golden evaluation set and actually run it

`eval/golden_set.jsonl` currently has **3 placeholder questions** with
`"REPLACE_WITH_REAL_DOC_ID"` as the expected doc_id — this is a template,
not a real eval set. The implementation plan requires a minimum of 25.

Once you've ingested a real corpus (Step 4), write 25+ real questions
against documents you actually ingested, with correct `doc_id` values (you
can find these in `data/processed/manifest.jsonl`).

`eval/run_eval.py`'s `main()` function currently raises
`NotImplementedError` — the scoring logic it calls
(`evaluate_recall_at_k`, `evaluate_citation_faithfulness`) is already
implemented and unit-tested (`backend/tests/test_eval_harness.py`), but
`main()` needs you to wire up a real `RagPipeline` instance (use
`backend.api.dependencies.get_rag_pipeline()` directly, or construct one the
same way) instead of raising. Then implement the `--compare-embeddings`
flag's actual A/B loop: run `evaluate_recall_at_k` once with
`NeuML/pubmedbert-base-embeddings`, once with a general-purpose model like
`BAAI/bge-base-en-v1.5`, and report both — this comparison is called out
explicitly in the implementation plan as required, not optional.

```bash
python eval/run_eval.py --golden-set eval/golden_set.jsonl --compare-embeddings
```

Do not consider this project "done" until this produces a real report with
real numbers — this was flagged in the original plan as the most common way
this class of project fails to hold up under technical interview scrutiny,
and it's the single most important remaining step.

## Step 6 — Smaller polish items (lower priority, do after Steps 1–5)

- `pdf_parser.py`'s table detection is a whitespace-heuristic, documented as
  approximate. If you have time, swap in PyMuPDF's `page.find_tables()` API
  (available in recent versions) for real table detection — the interface
  (`Block` with `block_type=ChunkType.TABLE`) doesn't need to change.
- The reranker flag exists but does nothing (see `DECISIONS.md`) — wire in
  a real `CrossEncoder` re-ranking step if `RERANKER_ENABLED=true`.
- No auth is enforced on `/api/health` (intentionally, so orchestrators can
  health-check without a token) — confirm this is the behavior you want in
  your deployment context.
- `backend/utils/logging_config.py` is wired into `main.py` but not into the
  Celery worker process — add `configure_logging()` to
  `backend/workers/celery_app.py` if you want JSON logs from the worker too.

## What NOT to redo

Everything in `backend/core/chunking.py`, `backend/utils/dedup.py`,
`backend/core/vector_store.py`'s hybrid search and payload filtering,
`backend/utils/taxonomy_client.py`, `backend/core/rag_pipeline.py`'s
citation-checking, and the FastAPI routes in `backend/api/routes.py` are
implemented and pass real (not smoke) tests — including tests that exercise
genuine edge cases (table-splitting boundaries, hallucinated citations,
payload filter correctness, cache-hit behavior). Don't rewrite these; if you
find a bug, fix it and add a regression test rather than restructuring.
