# PaleoRAG — Phylogenetic Context Engine

A RAG-powered search engine over open-access paleogenomics literature, with
hybrid (dense + sparse) retrieval, taxonomy-aware query expansion, and
citation-faithfulness checking on generated answers.

This repository was scaffolded by an AI coding agent against the spec in
`paleo_rag_agent_implementation_plan.md`. **See `HANDOFF.md` before running
anything** — it lists exactly what is implemented + tested vs. what still
needs live verification on a machine with full network/model access.

## Quick status

- ✅ 33/33 automated tests passing (`pytest backend/tests/`)
- ✅ Structure-aware chunking, dedup, taxonomy resolution, hybrid vector
  search, citation-faithfulness checking, and the FastAPI surface are all
  implemented and unit/integration tested (with mocked external services
  where a live network call would otherwise be required).
- ⚠️ Not yet run live: real PMC OA / bioRxiv / GBIF / PBDB API calls, real
  Ollama/Anthropic generation, real Celery+Redis broker execution, real
  sentence-transformers embedding model download. See `HANDOFF.md`.

## Running

```bash
cp .env.example .env        # edit values, especially API_BEARER_TOKEN
docker-compose up --build
```

Once containers are healthy:

```bash
# Pull the local LLM (one-time, manual step — not automated by compose)
docker exec -it paleo_rag-ollama-1 ollama pull llama3.1:8b

# Ingest a small batch of open-access papers
python -m backend.utils.pmc_oa_connector --query "ancient DNA" --limit 20

# Check health
curl http://localhost:8000/api/health

# Ask a question (SSE stream)
curl -N -X POST http://localhost:8000/api/chat/stream \
  -H "Authorization: Bearer $API_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What genetic evidence exists for Smilodon population decline?"}'
```

## Running tests

```bash
pip install -r requirements.txt
pytest backend/tests/ -v
```

All 33 tests run without Docker, without a live network connection, and
without downloading any ML model — they use Qdrant's embedded in-memory
mode and mock LLM/embedding backends. This is intentional: it means CI can
run this suite anywhere.

## Repository structure

See `paleo_rag_agent_implementation_plan.md` for the authoritative structure
and phase-by-phase spec this repo was built against.

## Documents in this repo

- `paleo_rag_agent_implementation_plan.md` — the original spec.
- `HANDOFF.md` — what's done, what's not, and exact next steps for whichever
  agent/developer picks this up next.
- `DECISIONS.md` — every place the spec said "choose and document," logged.
- `eval/` — evaluation harness (Recall@k, citation faithfulness). Logic is
  unit tested; running it against a real corpus is a HANDOFF.md next step.
