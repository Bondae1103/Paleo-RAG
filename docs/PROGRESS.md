# PaleoRAG Development Progress

## Phase 0: Repo Audit
- **Status**: COMPLETED
- **Tests Passing**: 44 / 44 (100%) in 63.93s
- **Key Findings**:
  - Existing RAG ingestion, PubMedBERT embeddings, BM25Okapi, RRF ($k=60$), Celery tasks, and citation auditor are fully functional and pass tests.
  - Core molecular biological databases (NCBI GenBank, UniProt, RCSB PDB, Pfam, PROSITE, GO, KEGG, STRING, Ensembl, UCSC) and Sequence Workbench were missing.
  - Verified live database identifiers and corrected discrepancies in `docs/DISCREPANCIES.md` (e.g. Mammoth HBB UniProt `D3U1H9` & PDB `3VRF`; Pla UniProt `P17811`, PDB `2X55`, Pfam `PF01278`; FOXP2 PROSITE `PS00658`).
  - Created `docs/AUDIT.md`, `docs/PLAN.md`, `docs/DISCREPANCIES.md`, and `docs/BLOCKERS.md`.

## Phase 1: Foundations
- **Status**: COMPLETED
- **Tests Passing**: 52 / 52 (44 baseline + 8 new foundations tests, 100%)
- **Delivered**:
  - Installed `biopython==1.84` in `.venv` and updated `requirements.txt`.
  - Configured centralized bio database endpoints, rate limiting, and cache settings in `backend/config.py` and `.env.example`.
  - Created error hierarchy in `backend/utils/error_types.py`.
  - Built `BioHttpClient` in `backend/utils/http_client.py` with disk caching, per-host throttling (NCBI, UniProt, RCSB PDB, STRING), exponential backoff retries, and NCBI etiquette headers.
  - Defined normalized Pydantic schemas in `backend/api/bio_schemas.py` for sequences, protein records, structures, domains, pathways, and interactions.
  - Implemented `/api/bio/health` endpoint and mounted `bio_router` into FastAPI `app`.

## Phase 2: Sequence Workbench (Module 1)
- **Status**: COMPLETED
- **Tests Passing**: 63 / 63 (44 baseline + 8 foundations + 11 sequence workbench tests, 100%)
- **Delivered**:
  - Implemented sequence validation and type detection (DNA, RNA, protein) in `backend/utils/sequence_tools.py`.
  - Added metrics computation: length, GC%, molecular weight (kDa), ambiguity index, and IUPAC validation.
  - Built bidirectional format converter between FASTA, GenBank flatfile, and EMBL formats using `Bio.SeqIO` with metadata synthesis (`molecule_type`).
  - Built Central Dogma engine: DNA $\rightarrow$ RNA transcription, reverse transcription, reverse complement, six-frame translation (+1..+3, -1..-3), and open reading frame (ORF) detection with start/stop codons and genomic coordinates.
  - Implemented GenBank/EMBL-style submission metadata validator.
  - Mounted `/api/bio/sequence/validate`, `/api/bio/sequence/convert`, `/api/bio/sequence/dogma`, and `/api/bio/sequence/submission-check` endpoints.

## Phases 3–6: Molecular DB Clients, Structure, Pathways & Genomics (Modules 2, 3, 4, 5, 6)
- **Status**: COMPLETED
- **Tests Passing**: 77 / 77 (100% passing across all 14 test modules)
- **Delivered**:
  - **NCBI Client (`backend/utils/ncbi_client.py`)**: ESearch, ESummary, EFetch for nucleotide accessions, GenBank flatfiles, and mitochondrial genomes with normalized `SequenceRecord` schema.
  - **UniProt Client (`backend/utils/uniprot_client.py`)**: Swiss-Prot & TrEMBL parser extracting active sites, binding sites, disulfide bonds, PTMs, and legacy PIR cross-references.
  - **ENA & DDBJ Client (`backend/utils/ena_ddbj_client.py`)**: ENA Browser & Portal API integration with INSDC cross-mirroring.
  - **Taxonomic Expansion Flag (`backend/core/rag_pipeline.py`)**: Added `query_expansion_enabled` and `enable_query_expansion` flag for A/B testing; updated `TaxonResolution` with lineage and confidence.
  - **PDB & CATH/SCOP Client (`backend/utils/pdb_client.py`)**: RCSB PDB metadata and coordinate fetcher, PDBe SIFTS fold lookups (CATH & SCOP), and residue mutation mapping engine for 3D viewer.
  - **Functional & Mining Client (`backend/utils/functional_client.py`)**: Offline-capable PROSITE regex motif scanner (`prosite_to_regex`), Pfam domain lookup via InterPro, KEGG REST pathways, and STRING DB protein-protein interaction networks with evidence channels.
  - **Comparative Genomics Client (`backend/utils/genomics_client.py`)**: Ensembl gene coordinates, UCSC Human Genome Browser gateway link generator with Altai Neanderthal / Denisovan tracks, and NCBI GEO accessions.
  - **Unified BioAggregator (`backend/utils/bio_aggregator.py`)**: Multi-database cross-referencing engine resolving literature entities to primary molecular records in a single call.
  - **API Router (`backend/api/bio_routes.py`)**: Added endpoints for `/api/bio/nucleotide/*`, `/api/bio/protein/*`, `/api/bio/structure/*`, `/api/bio/motifs/*`, `/api/bio/pathways/*`, `/api/bio/interactions/*`, `/api/bio/locus/*`, and `/api/bio/lookup/*`.

## Phase 7: RAG Grounding & Dual-Pane Output
- **Status**: COMPLETED
- **Tests Passing**: 78 / 78 passing (including `backend/tests/test_vector_store.py::test_rrf_scoring_formula_on_toy_ranking`)
- **Delivered**:
  - Integrated `BioAggregator` into `/api/chat/stream` SSE generator: terminal event emits `bio_cards` payload alongside retrieved literature chunks and citation warnings.
  - Added mathematical proof test for Reciprocal Rank Fusion ($k=60$) verifying rank inversion immunity.

## Phase 8: Golden Set Expansion & Model Comparison
- **Status**: COMPLETED
- **Delivered**:
  - Evaluated 27-question golden set in `eval/run_eval.py`.
  - Added `--compare-embeddings` option comparing hybrid dense+sparse (PubMedBERT + BM25 + RRF) with sparse BM25 baseline.

## Phase 9 / Module 7: Distributed Architecture & Docker Compose
- **Status**: COMPLETED
- **Delivered**:
  - Multi-stage `frontend/Dockerfile` using Node 20 Alpine builder and Nginx Alpine runner.
  - Configured `frontend/nginx.conf` with Single Page Application routing, API proxying, and unbuffered SSE stream passthrough (`proxy_buffering off`, `proxy_read_timeout 600s`).
  - Updated `docker-compose.yml` adding `frontend` service on port 3000 with healthcheck and service dependencies.

## Phase 10: Frontend UI Integration
- **Status**: COMPLETED
- **TypeScript & Build**: 0 errors (`npm run check` clean, `npm run build` bundled 1624 modules in 21.6s).
- **Delivered**:
  - Added full TypeScript schemas and fetch methods to `frontend/client/src/lib/api.ts`.
  - Built `SequenceWorkbenchView.tsx`: IUPAC sequence analyzer, bidirectional format converter, Central Dogma 6-frame translation with ORF detector, and INSDC submission metadata validator.
  - Built `BioDatabaseView.tsx`: Unified search bar, quick case studies selector, multi-database cards, interactive PROSITE motif scanner, and STRING interaction filter.
  - Built `MolecularViewer.tsx`: WebGL 3D structure viewer powered by 3Dmol.js with Cartoon, Stick, Sphere representations, auto-spin, and paleogenomic mutation highlighting.
  - Built `BioEntityCard.tsx`: Dual-pane grounded entity card embedded inside `EvidenceDrawer` in `StudioView`.
  - Mounted `"workbench"` and `"biodb"` views in `Home.tsx` navigation rail.

## Phase 11: Pre-Configured Case Studies
- **Status**: COMPLETED
- **Delivered**:
  - Case Study 1: Mammoth HBB (*Mammuthus primigenius* — `HQ184444.1`, `D3U1H9`, `3VRF`, `PF00042`, `PS01033`).
  - Case Study 2: Neanderthal FOXP2 (*Homo neanderthalensis* — `AF512946.1`, `O15409`, `2A07`, `PF00250`, `PS00658`).
  - Case Study 3: Ancient *Y. pestis* Pla (*Yersinia pestis* — `AL590842.1`, `P17811`, `2X55`, `PF01278`, `PS00834`, `map05100`).
  - Integrated 1-click preset buttons across `BioDatabaseView` and `StudioView`.

## Phase 12: Benchmark Suite Execution
- **Status**: COMPLETED
- **Delivered**:
  - Executed `eval/run_eval.py --compare-embeddings`.
  - **Recall@5**: **100.00%** (27 / 27).
  - **Citation Faithfulness**: **96.30%** (26 / 27).
  - Saved live evaluation report to `eval/latest_report.md`.

## Phase 13: Documentation & Syllabus Mapping
- **Status**: COMPLETED
- **Delivered**:
  - Authored `docs/SYLLABUS_MAP.md` mapping every module (CO1–CO6) to exact files, endpoints, UI views, and tests.
  - Updated `README.md` with complete architectural overview, biological databases integration, and quickstart guide.
