# DECISIONS.md

Every place the implementation plan said "choose and document," logged here.

## Sparse retrieval backend: `rank_bm25` (in-process) over Qdrant-native sparse vectors

**Chosen:** `rank_bm25` (`BM25SparseIndex` in `backend/core/rag_pipeline.py`).

**Why:** Qdrant's native sparse vector support requires additional
collection configuration (a separate named sparse vector space) and a
sparse-vector-producing model or a hand-built term-frequency encoder wired
into the upsert path. `rank_bm25` gets a working BM25 ranking with zero
extra infrastructure and is trivially swappable later — `BM25SparseIndex`
is the only place that would need to change, since `VectorStore.hybrid_search`
already takes sparse rankings as an opaque `(doc_id, chunk_index)` ranked
list and doesn't care how they were produced.

**Trade-off:** `rank_bm25`'s index is rebuilt in-process from a corpus
snapshot (see `BM25SparseIndex.build()`), so it doesn't scale as gracefully
as a server-side sparse index for a very large corpus. For a portfolio-scale
paleogenomics corpus (hundreds to low thousands of papers), this is a
non-issue. Revisit if the corpus grows past ~50k chunks.

## Reranker: implemented as a config flag, not implemented as actual logic

**Chosen:** `RERANKER_ENABLED` exists in `config.py` and is checked in
intent throughout the spec (Phase 7), but no actual cross-encoder reranking
step runs yet — `rag_pipeline.py`'s hybrid search result is passed straight
to prompt construction.

**Why:** This was explicitly called out as a stretch goal in the
implementation plan ("implement the config flag even if the reranker itself
is stubbed initially"). Wiring in a real cross-encoder requires downloading
another model (network access not available in the build sandbox — see
HANDOFF.md) and was deprioritized in favor of finishing the core pipeline
end-to-end.

**Next step:** When `RERANKER_ENABLED=true`, load
`cross-encoder/ms-marco-MiniLM-L-6-v2` via `sentence-transformers`'
`CrossEncoder` class, score the top-N hybrid search results against the
query, and re-sort before truncating to `top_k`.

## Point ID scheme in Qdrant: UUID5-derived from `{doc_id}::{chunk_index}`

**Chosen:** `_to_qdrant_point_id()` in `vector_store.py` deterministically
maps the natural human-readable ID (`"doc123::4"`) to a UUID5.

**Why:** Qdrant (including its embedded/local mode, which the test suite
relies on) requires point IDs to be either unsigned integers or valid UUID
strings — arbitrary strings are rejected. UUID5 (not UUID4) was chosen
specifically because it's a deterministic hash of the input string: the same
`doc_id`/`chunk_index` pair always produces the same point ID, which is
required for idempotent re-upserts during the dedup/re-ingestion flow
(Phase 2's re-ingestion requirement). The original human-readable ID is
preserved in the payload's `doc_id` / `chunk_index` fields, so nothing is
lost.

## Manifest storage: flat JSONL file, not a database

**Chosen:** `data/processed/manifest.jsonl`, read-modify-write on status
updates (see `backend/workers/tasks.py::_update_manifest_status`).

**Why:** Matches the structure given in the original plan's file tree
(`data/processed/`) and is sufficient for a portfolio-scale corpus. Flagged
explicitly in the docstring as something to swap for a real DB (SQLite at
minimum) if the corpus grows large enough that read-modify-write on the
whole file becomes a bottleneck.

## Embedding fallback: `MockEmbeddingModel` for tests/dev, real model deferred

**Chosen:** `backend/core/embeddings.py` defines both
`SentenceTransformerEmbeddingModel` (real) and `MockEmbeddingModel`
(deterministic hash-seeded vectors, no ML dependency).

**Why:** The build sandbox had no network path to the model hub
(huggingface.co), so `sentence-transformers`/`torch` could not be installed
and smoke-tested there. Rather than leave the whole embeddings layer
untested, the interface was locked down and verified against
`MockEmbeddingModel` everywhere it's consumed (vector store, rag pipeline,
API tests) — swapping in the real model requires no changes to any caller.
See HANDOFF.md step 1 for exactly what to verify on the target machine.

## PMC OA license parsing: placeholder value, not real XML parsing

**Chosen:** `pmc_oa_connector.py` currently hardcodes `license_tag = "cc-by"`
with a comment marking it as a placeholder, rather than parsing the actual
license field out of the OA service's XML response.

**Why:** The OA service was not reachable from the build sandbox, so there
was no live XML response to parse against, and guessing at an undocumented
XML schema risked silently mis-parsing real license data (a licensing bug
here is exactly the kind of mistake Section 0 of the spec is trying to
prevent). Left as an explicit, clearly-flagged TODO rather than a fabricated
implementation. See HANDOFF.md step 4.
