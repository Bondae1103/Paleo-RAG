# Phase 0 Audit: PaleoRAG (Phylogenetic Context Engine)

**Audit Date**: September 28, 2026  
**Auditor**: Antigravity Agent  
**Environment**: Python 3.11.9, Node v20+, Windows (PowerShell)  
**Existing Test Status**: 44 / 44 tests passing (100%) in 63.93s  

---

## 1. Repository Layout & Existing Architecture

```
paleo_rag/
├── backend/
│   ├── api/
│   │   ├── dependencies.py      # Dependency injection (VectorStore, RagPipeline, auth)
│   │   ├── routes.py            # Endpoints: /api/upload, /api/ingest, /api/task/{id}, /api/chat/stream, /api/health, /api/documents, /api/eval/summary
│   │   └── schemas.py           # Pydantic schemas (ChatRequest, HealthResponse, etc.)
│   ├── core/
│   │   ├── chunking.py          # Section-aware chunker, atomic tables/captions, content hash
│   │   ├── embeddings.py        # PubMedBERT (NeuML/pubmedbert-base-embeddings, 768-d)
│   │   ├── llm_client.py        # OllamaClient, AnthropicClient, MockLLMClient
│   │   ├── query_expansion.py   # Query expansion via TaxonomyClient
│   │   ├── rag_pipeline.py      # RagPipeline, BM25SparseIndex, build_prompt, check_citations
│   │   └── vector_store.py      # Qdrant client, UUID5 deterministic point IDs, RRF (k=60)
│   ├── utils/
│   │   ├── biorxiv_connector.py # Direct bioRxiv PDF downloader
│   │   ├── dedup.py             # Incremental deduplication & stale chunk detector
│   │   ├── logging_config.py    # Structured JSON / console logger
│   │   ├── pbdb_connector.py    # Paleobiology Database API connector
│   │   ├── pdf_parser.py        # PyMuPDF PDF parser + JATS XML parser
│   │   ├── pmc_oa_connector.py  # NCBI PMC Open Access E-utilities + JATS XML
│   │   └── taxonomy_client.py   # GBIF Backbone + PBDB fallback resolver with cache
│   ├── workers/
│   │   ├── celery_app.py        # Celery application initialization
│   │   └── tasks.py             # Celery chain: extract -> parse -> chunk -> embed -> upsert
│   ├── config.py                # Pydantic Settings reading .env
│   └── main.py                  # FastAPI app factory, CORS, router mounting
├── data/
│   ├── processed/manifest.jsonl # Ingested literature manifest
│   ├── qdrant_storage/          # Embedded local Qdrant vectors
│   └── raw_pdfs/                # Downloaded PMC XML and bioRxiv PDFs
├── eval/
│   ├── golden_set.jsonl         # 27 peer-reviewed benchmark questions
│   ├── latest_report.md         # Evaluated metrics report
│   └── run_eval.py              # Benchmark execution harness
├── frontend/
│   ├── client/src/
│   │   ├── pages/Home.tsx       # Primary SPA: Research Studio, Corpus, Evaluation, Diagnostics
│   │   ├── lib/api.ts           # API client (fetch, SSE reader, auth headers)
│   │   └── components/          # Radix UI + Lucide components
│   ├── package.json             # Vite 7, React 19, Tailwind CSS v4
│   └── vite.config.ts           # Dev server with proxy to localhost:8000
├── tests/ (backend/tests/)      # 10 test files covering all backend modules
├── docker-compose.yml           # Services: redis, qdrant, ollama, api, worker (frontend missing)
├── Dockerfile                   # Python 3.12-slim container definition
└── requirements.txt             # Pinned dependencies
```

---

## 2. RAG Pipeline Operational Audit

1. **Document Chunk Schema**:
   * Stored in Qdrant with payload:
     `{"doc_id": str, "chunk_index": int, "section": str, "chunk_type": "text"|"table"|"caption", "text": str, "content_hash": str, "taxon_scientific_name": str, "geological_period": str, "publication_year": int}`
   * Content hashing via SHA-256 over normalized text (`backend/core/chunking.py:compute_content_hash`).
2. **Point ID Scheme**:
   * Deterministic UUID5 generated from `{doc_id}::{chunk_index}` with namespace `UUID("a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d")` (`backend/core/vector_store.py:_to_qdrant_point_id`).
   * Guarantees idempotent re-ingestion, in-place updates, and clean chunk deletions.
3. **Embedding Model**:
   * Active: `NeuML/pubmedbert-base-embeddings` (768 dimensions), batch size 32 (`backend/core/embeddings.py:PubMedBERTEmbedding`).
4. **Vector Store & Hybrid Retrieval**:
   * Qdrant collection `paleo_chunks` with Cosine distance.
   * Sparse retrieval via `BM25Okapi` (`rank_bm25` library in `backend/core/rag_pipeline.py:BM25SparseIndex`), synchronized from vector store chunks.
   * Rank fusion: Reciprocal Rank Fusion (RRF, $k=60$):
     $$\text{RRF Score}(d) = \frac{1}{60 + r_{\text{dense}}(d)} + \frac{1}{60 + r_{\text{sparse}}(d)}$$
     Implemented in `backend/core/vector_store.py:VectorStore.hybrid_search`.
5. **LLM Inference & Prompting**:
   * Prompt template enforces strict grounding and exact marker syntax `[doc_id:chunk_index]` (`backend/core/rag_pipeline.py:PROMPT_TEMPLATE`).
   * Streaming support via `stream_chat_query` SSE endpoint (`backend/api/routes.py:chat_stream`).
6. **Citation Auditor**:
   * Regex `\[([\w\-.]+):(\d+)\]` extracts all cited markers from LLM output.
   * Validates every marker against the set of retrieved `(doc_id, chunk_index)` pairs.
   * Flags any ungrounded / hallucinated citation with a reason object (`backend/core/rag_pipeline.py:check_citations`).

---

## 3. Frontend Audit

* **Framework**: React 19, TypeScript 5.6, Tailwind CSS v4, Vite 7, Lucide icons, Sonner toasts.
* **Views in `Home.tsx`**:
  * `studio` (Research Studio): Fully wired to real `/api/chat/stream` SSE endpoint with interactive evidence pane and citation auditing badges.
  * `corpus` (Literature Corpus): Wired to `/api/documents`, `/api/upload`, and `/api/ingest`.
  * `evaluation` (Benchmark Eval): Wired to `/api/eval/summary`.
  * `diagnostics` (Diagnostics): Wired to `/api/health`.
* **Gaps**:
  * No Sequence Workbench view exists.
  * No BioDB Explorer view exists.
  * No 3D molecular viewer is integrated.
  * Molecular records (GenBank/UniProt/PDB/STRING) are not rendered alongside literature chunks.

---

## 4. Feature Checklist & Status Matrix

| Component / Requirement | Status | Evidence (Files & Symbols) | Gap Description / Action Required |
| :--- | :--- | :--- | :--- |
| **Sequence Validation (IUPAC)** | **MISSING** | None | Need DNA/RNA/Protein detection, IUPAC symbol validation, GC%, MW (kDa), and ambiguity index calculations. |
| **Sequence Format Interconversions** | **MISSING** | None | Need Biopython `Bio.SeqIO` integration for FASTA $\leftrightarrow$ GenBank $\leftrightarrow$ EMBL format conversion. |
| **Central Dogma Engine** | **MISSING** | None | Need DNA $\rightarrow$ RNA transcription, cDNA reverse transcription, 6-frame translation (+1..+3, -1..-3), and ORF detection. |
| **Submission Metadata Validator** | **MISSING** | None | Need schema validator for GenBank-style sequence submission forms. |
| **NCBI E-utilities (GenBank/Nucleotide)** | **MISSING** | `backend/utils/pmc_oa_connector.py` only handles PMC full-text XML | Need ESearch, EFetch, ESummary for nucleotide accessions and mitochondrial genomes. |
| **ENA & DDBJ Mirroring** | **MISSING** | None | Need REST lookup to ENA portal API and DDBJ cross-referencing. |
| **UniProtKB & PIR Client** | **MISSING** | None | Need UniProtKB REST client fetching Swiss-Prot/TrEMBL entries, active sites, PTMs, and PIR cross-references. |
| **RCSB PDB Client & 3D Viewer** | **MISSING** | None | Need RCSB REST API client, 3D Mol* or 3Dmol.js viewer in frontend, and coordinate/metadata parser. |
| **CATH & SCOP Classifications** | **MISSING** | None | Need CATH API / PDBe annotation client to fetch Class-Architecture-Topology-Homology and SCOP folds. |
| **Pfam & PROSITE Mining** | **MISSING** | None | Need InterPro/Pfam domain lookup and PROSITE signature scanner + local regex pattern finder. |
| **GO & KEGG Integration** | **MISSING** | None | Need Gene Ontology (BP/MF/CC) and KEGG pathway mapping (`map05100`). |
| **STRING & BioGRID Networks** | **MISSING** | None | Need STRING DB REST client for PPI subgraphs and optional BioGRID integration with graceful fallback. |
| **Ensembl & UCSC Deep Links** | **MISSING** | None | Need Ensembl REST client for orthologs/synteny and UCSC Genome Browser track link generators (GRCh38, Altai Neanderthal). |
| **Taxonomic Query Expansion** | **DONE** | `backend/utils/taxonomy_client.py:TaxonomyClient.resolve`, `backend/core/query_expansion.py:expand_query` | Fully functioning with GBIF Backbone, PBDB fallback, and 30-day cache. |
| **Hybrid Retrieval (PubMedBERT + BM25 + RRF)** | **DONE** | `backend/core/vector_store.py:VectorStore.hybrid_search`, `backend/core/rag_pipeline.py:BM25SparseIndex` | Fully functioning with $k=60$ RRF fusion. |
| **LLM Streaming & Citations** | **DONE** | `backend/api/routes.py:chat_stream`, `backend/core/rag_pipeline.py:RagPipeline.query_stream` | Fully functioning SSE endpoint. |
| **Citation Auditor** | **DONE** | `backend/core/rag_pipeline.py:check_citations` | Fully functioning with ungrounded citation warnings. |
| **Literature-to-Molecular Entity Linking** | **MISSING** | None | Need entity extractor in RAG pipeline linking extracted genes/species to primary biological IDs. |
| **Distributed Architecture (Celery, Redis, Docker)** | **PARTIAL** | `docker-compose.yml`, `backend/workers/tasks.py` | Redis, Qdrant, Ollama, API, and Worker exist. Frontend is missing from `docker-compose.yml`. |
| **Three Verified Case Studies** | **MISSING** | None | Need pre-configured verified case studies (Mammoth HBB `HQ184444.1`/`D3U1H9`/`3VRF`, Neanderthal FOXP2 `AF512946.1`/`O15409`/`2A07`, Y. pestis Pla `AL590842.1`/`P17811`/`2X55`). |
| **Evaluation Benchmark Harness** | **DONE** | `eval/run_eval.py`, `eval/golden_set.jsonl` | 27 queries, 100% recall@5, 100% citation faithfulness on literature. |
| **Syllabus Mapping Document** | **MISSING** | None | Need `docs/SYLLABUS_MAP.md` covering all 7 course modules (CO1–CO6). |

---

## 5. Prioritized Gap List

1. **Foundations & Shared HTTP Client**: Centralized HTTP client with rate limiting, retries, exponential backoff, caching, and unified Pydantic schemas.
2. **Sequence Workbench Backend & Tests**: Biopython `SeqIO` format converter, Central Dogma engine, 6-frame translation, ORF detection, and IUPAC validation.
3. **Biological Database Clients & Tests**:
   - NCBI GenBank / E-utilities, ENA, DDBJ.
   - UniProtKB (Swiss-Prot/TrEMBL) + PIR cross-references.
   - RCSB PDB + CATH + SCOP classification.
   - STRING, Pfam (InterPro), PROSITE regex miner, GO, KEGG.
   - Ensembl REST + UCSC Genome Browser links + GEO links.
4. **Dual-Pane Entity Linking**: Link retrieved literature entities to live molecular database cards in the RAG stream.
5. **Frontend Extensions**:
   - Add Sequence Workbench view.
   - Add BioDB Explorer view with 3D structure viewer (3Dmol.js / Mol*).
   - Add dual-pane Molecular Info Cards in Research Studio.
   - Wire all controls to real backend endpoints.
6. **Case Studies & Verification**: Pre-configured verified case studies incorporating corrected accessions (`docs/DISCREPANCIES.md`).
7. **Distributed Architecture Completion**: Add frontend container and health checks to `docker-compose.yml`.
8. **Documentation**: Write `docs/SYLLABUS_MAP.md` and complete progress reports.
