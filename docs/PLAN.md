# PaleoRAG Execution Plan: Biological Databases Implementation

Based on the findings from [docs/AUDIT.md](file:///c:/Users/Anoop/Documents/Projects/Tech/Ongoing/paleo_rag/docs/AUDIT.md) and [docs/DISCREPANCIES.md](file:///c:/Users/Anoop/Documents/Projects/Tech/Ongoing/paleo_rag/docs/DISCREPANCIES.md), this plan re-orders and groups the required implementation phases. Completed components (hybrid vector store, BM25 index, basic taxonomy expansion, citation auditor) are preserved and extended rather than rewritten.

---

## Phase Overview and Execution Order

```
[Phase 0: Repo Audit] (COMPLETED)
       │
       ▼
[Phase 1: Foundations]
   - Install biopython
   - Shared HTTP Client with rate-limiting, retries, and disk/Redis cache
   - Normalized Pydantic schemas (SequenceRecord, ProteinRecord, StructureRecord, etc.)
   - Modular Bio API skeleton and health check
       │
       ▼
[Phase 2: Sequence Workbench (Module 1)]
   - Biopython SeqIO format conversion (FASTA ↔ GenBank ↔ EMBL)
   - Central Dogma (DNA → RNA, reverse transcription, 6-frame translation, ORF finder)
   - Validation & metrics (IUPAC, GC%, MW in kDa, ambiguity index)
   - Submission-metadata validator
   - Comprehensive unit tests
       │
       ▼
[Phase 3: Primary Molecular Database Clients (Module 3)]
   - NCBI E-utilities (ESearch, EFetch, ESummary for nucleotides/genomes)
   - ENA & DDBJ cross-mirroring integration
   - UniProtKB REST client (Swiss-Prot, TrEMBL, active sites, PTMs, PIR xrefs)
   - Normalized responses with unit and mock tests
       │
       ▼
[Phase 4: Structure, Folds & Classifications (Module 4)]
   - RCSB PDB metadata & coordinate fetcher
   - CATH & SCOP classification lookups
   - Mutation mapping engine (ancestral vs. modern residue numbering & highlight ranges)
       │
       ▼
[Phase 5: Pathways, Interactions & Mining (Module 5 & Module 2)]
   - Pfam domains (InterPro API) & PROSITE pattern scanner + local regex miner
   - Gene Ontology (QuickGO / UniProt terms) & KEGG REST pathway mapping
   - STRING DB protein-protein interaction network client
   - BioGRID optional client with graceful fallback
       │
       ▼
[Phase 6: Comparative Genomics & Track Linking (Module 6)]
   - Ensembl REST client (orthology, synteny, exon boundaries)
   - UCSC Human Genome Browser deep-link generator (GRCh38 vs. Altai Neanderthal)
   - NCBI GEO accession linkage
       │
       ▼
[Phase 7: RAG Pipeline Grounding & Dual-Pane Output]
   - Literature-to-molecular entity extraction in RagPipeline
   - Dual-pane response payload: literature answer + live molecular cards
   - Unit test on toy ranking verifying RRF formula Σ 1/(k + rank_m(d))
       │
       ▼
[Phase 8: Frontend Evolution]
   - Sequence Workbench UI: conversion tool, 6-frame viewer, ORF visualization
   - BioDB Explorer UI: GenBank, UniProt, 3D structure viewer (3Dmol.js / Mol*), STRING graph
   - Dual-pane Molecular Info Cards inside Research Studio
   - Real backend integration (no mocked responses)
       │
       ▼
[Phase 9: Demonstration Case Studies (Phase 11)]
   - Pre-configured verified case studies using authentic accessions:
     * Woolly Mammoth Hemoglobin: GenBank HQ184444.1, UniProt D3U1H9, PDB 3VRF/3VRE
     * Neanderthal FOXP2: GenBank AF512946.1, UniProt O15409, PDB 2A07, Pfam PF00250, PROSITE PS00658
     * Ancient Y. pestis Pla: GenBank AL590842.1, UniProt P17811, PDB 2X55, Pfam PF01278
       │
       ▼
[Phase 10: Distributed Architecture & Docker Compose (Module 7)]
   - Add frontend service to docker-compose.yml
   - Verify asynchronous Celery task ingestion end-to-end
   - Document single-command startup
       │
       ▼
[Phase 11: Benchmark & Evaluation]
   - Execute evaluation harness on golden set
   - Verify Recall@5, MRR, and citation faithfulness
   - Persist results to JSON and update diagnostics UI
       │
       ▼
[Phase 12: Documentation & Syllabus Mapping]
   - docs/SYLLABUS_MAP.md mapping 7 modules (CO1–CO6) to concrete code files
   - Updated README with architecture diagram, screenshots, and run guide
   - Final end-to-end verification and progress report
```

---

## Work Guidelines

1. **Commit Groups**: Work phase by phase. Keep each phase atomic and verified.
2. **Real Data**: No fake data or stubbed responses. All external endpoints query live APIs with disk/Redis caching and graceful fallback.
3. **Tests**: Unit tests for every module; mocked tests for external APIs; mark integration tests appropriately.
4. **Discrepancy Discipline**: Any deviation from the user's preliminary spec must adhere to `docs/DISCREPANCIES.md`.
