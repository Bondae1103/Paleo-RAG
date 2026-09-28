# PaleoRAG Project Blockers & Graceful Degradation Log

This document records API key requirements, network access constraints, and rate limiting policies across external biological databases, along with the implemented fallbacks.

---

## 1. BioGRID Access Key
* **Constraint**: BioGRID REST API requires an `accesskey` parameter obtained via free academic registration.
* **Resolution**: BioGRID is made optional. When `BIOGRID_API_KEY` is not present in `.env`, the system gracefully bypasses BioGRID and relies on **STRING DB** (which is open, keyless, and provides extensive confidence scores and evidence channels).

## 2. NCBI E-utilities Rate Limiting
* **Constraint**: NCBI enforces a rate limit of 3 requests/second without an API key (10 requests/second with `NCBI_API_KEY`). Requests must include `email` and `tool` parameters per NCBI etiquette.
* **Resolution**: All NCBI requests are channeled through a centralized HTTP client (`backend/utils/http_client.py`) that includes `NCBI_EMAIL`, `NCBI_API_KEY`, automatic exponential backoff retry on HTTP 429, and a TTL-based response cache (disk/Redis).

## 3. Local LLM / Ollama Dependency
* **Constraint**: Local execution of `llama3.2:1b` or `llama3.1:8b` requires Ollama running on `http://localhost:11434`.
* **Resolution**: The system supports 3 providers via `LLM_PROVIDER`: `ollama`, `anthropic`, and `mock`. In environments without Ollama or an Anthropic API key, `mock` provides deterministic responses allowing the full RAG pipeline, streaming SSE, and citation auditor to be tested without external services.

## 4. Qdrant Embedded vs. Server Mode
* **Constraint**: Dockerized Qdrant requires a running daemon on port 6333, which may not be running during standalone unit tests.
* **Resolution**: `QDRANT_USE_LOCAL_MODE=true` uses Qdrant's embedded storage in `./data/qdrant_storage`, allowing tests and local development to function without a running Docker container.
