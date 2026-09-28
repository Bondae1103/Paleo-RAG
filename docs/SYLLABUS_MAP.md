# Biological Databases Coursework Syllabus Mapping Matrix

**Project Name**: PaleoRAG (Phylogenetic Context Engine)  
**Coursework**: Biological Databases (CO1 – CO6)  
**Academic Level**: Advanced Undergraduate / Graduate Bioinformatics  

This document provides a comprehensive, rigorous mapping of every topic and Course Outcome (CO) from the Biological Databases syllabus to the specific backend code, API endpoints, frontend views, and automated test suites in the PaleoRAG codebase.

---

## High-Level Course Outcome (CO) Summary

| Course Outcome | Focus Area | Bloom's Taxonomy | Implementation Component in PaleoRAG |
|---|---|---|---|
| **CO 1** | Sequence Submission & Manipulation | Remember / Understand / Apply | `SequenceWorkbenchView`, `backend/utils/sequence_tools.py`, `/api/bio/sequence/*` |
| **CO 2** | Biological Data Integration & Mining | Remember / Understand / Apply / Analyze | `BioAggregator`, `RagPipeline`, Dual-Pane Grounding, Paleogenomic Case Studies |
| **CO 3** | Primary Molecular Databases | Understand / Apply | `ncbi_client.py` (GenBank), `ena_ddbj_client.py` (ENA/DDBJ), `uniprot_client.py` (UniProtKB/PIR) |
| **CO 4** | Secondary & Structural Databases | Understand / Apply | `functional_client.py` (PROSITE/Pfam), `pdb_client.py` (RCSB PDB, CATH, SCOP, 3Dmol WebGL) |
| **CO 5** | Specialized, Pathway & Interaction DBs | Understand / Apply | `functional_client.py` (KEGG & STRING DB), `genomics_client.py` (Ensembl & UCSC Archaic Tracks) |
| **CO 6** | Distributed Architecture & Federation | Apply / Create | Multi-container `docker-compose.yml`, Celery async ingestion, Redis broker, Qdrant vector engine |

---

## Detailed Module-by-Module Mapping

### Module 1: Sequence Submission Tools (CO: 1)

| Syllabus Topic | Bloom's Taxonomy | Backend Implementation | API Endpoint | Frontend UI View | Verification & Tests |
|---|---|---|---|---|---|
| **1. Relational database & motivation of biological databases** | Remember | `backend/utils/sequence_tools.py:validate_sequence_content` | `POST /api/bio/sequence/validate` | `SequenceWorkbenchView` (Tab 1: IUPAC Validator) | `backend/tests/test_sequence_workbench.py::test_detect_sequence_type` |
| **2. Central dogma of life** | Understand | `backend/utils/sequence_tools.py:execute_central_dogma` | `POST /api/bio/sequence/dogma` | `SequenceWorkbenchView` (Tab 3: Central Dogma & 6-Frame ORFs) | `backend/tests/test_sequence_workbench.py::test_central_dogma_transcription_and_orfs` |
| **3. Submission of sequences to the database** | Apply | `backend/utils/sequence_tools.py:validate_insdc_submission` | `POST /api/bio/sequence/submission-check` | `SequenceWorkbenchView` (Tab 4: Submission Validator) | `backend/tests/test_sequence_workbench.py::test_submission_metadata_validator` |
| **4. Sequence formats (FASTA, GenBank, EMBL)** | Apply | `backend/utils/sequence_tools.py:convert_sequence_format` | `POST /api/bio/sequence/convert` | `SequenceWorkbenchView` (Tab 2: Format Converter) | `backend/tests/test_sequence_workbench.py::test_convert_fasta_to_genbank` |
| **5 & 6. Interconversion of molecular sequences** | Apply | Biopython `Bio.SeqIO` bidirectional converter (`FASTA` $\leftrightarrow$ `GenBank` $\leftrightarrow$ `EMBL`) | `POST /api/bio/sequence/convert` | `SequenceWorkbenchView` (Interactive bidirectional converter with 1-click clipboard copy) | `backend/tests/test_sequence_workbench.py::test_convert_genbank_to_fasta` |

---

### Module 2: Biological Data Integration & Mining (CO: 2)

| Syllabus Topic | Bloom's Taxonomy | Backend Implementation | API Endpoint | Frontend UI View | Verification & Tests |
|---|---|---|---|---|---|
| **1. General data integration** | Remember | `backend/utils/bio_aggregator.py:BioAggregator` (federated dispatch across 8 independent databases) | `GET /api/bio/lookup/{query}` | `BioDatabaseView` (Unified multi-DB search bar) | `backend/tests/test_structure_pathways_genomics.py::test_unified_bio_lookup_mammoth` |
| **2. Major areas in biological data integration** | Understand | Cross-domain integration: Genomic (Ensembl/UCSC) + Proteomic (UniProt) + Structural (PDB) + Systems (KEGG/STRING) | `GET /api/bio/lookup/{query}` | `BioDatabaseView` (Structured dual-column multi-database cards) | `backend/tests/test_structure_pathways_genomics.py::test_api_structure_and_pathway_routes` |
| **3. Challenges in biological data integration** | Understand | Handled accession discrepancies, schema divergence, API rate-limits, and cross-mirror synchronization | `backend/utils/http_client.py` (DiskCache & Host Throttlers) | `BioDatabaseView` & `DiagnosticsView` | `backend/tests/test_foundations.py::test_disk_cache_roundtrip` & `test_rate_limiter_throttles` |
| **4. Artificial intelligence in data integration** | Apply | Hybrid RAG with PubMedBERT embeddings + BM25 + Reciprocal Rank Fusion ($k=60$) + Citation Auditing | `POST /api/chat/stream` | `StudioView` (Research Studio with dual-pane `BioEntityCard`) | `backend/tests/test_vector_store.py::test_rrf_scoring_formula_on_toy_ranking` |
| **5 & 6. Paleogenomic Case Studies** | Analyze | Verified ground truth: Mammoth HBB, Neanderthal FOXP2, Ancient *Y. pestis* Pla | `GET /api/bio/lookup/{query}` | One-click case study presets in `BioDatabaseView` & `StudioView` | Evaluated against 27-question benchmark in `eval/run_eval.py` (Recall@5: 100%) |

---

### Module 3: Primary Molecular Databases (CO: 3)

| Database Family | Core Databases | Backend Implementation | API Endpoint | Frontend UI View | Verification & Tests |
|---|---|---|---|---|---|
| **Nucleotide Databases (INSDC)** | **NCBI GenBank**, **EMBL-EBI ENA**, **DDBJ** | `backend/utils/ncbi_client.py` (E-utilities) & `backend/utils/ena_ddbj_client.py` (ENA Browser & Portal API) | `GET /api/bio/nucleotide/{acc}`, `GET /api/bio/ena/{acc}` | `BioDatabaseView` (Primary Nucleotide DB Card with direct external links) | `backend/tests/test_molecular_clients.py::test_ncbi_client_fetch_record`, `test_ena_client_fasta_and_filereport` |
| **Protein Sequence Databases** | **UniProtKB / Swiss-Prot**, **TrEMBL**, **PIR** | `backend/utils/uniprot_client.py` (UniProt REST API with active sites, PTMs, disulfides, PIR cross-refs) | `GET /api/bio/protein/{acc}` | `BioDatabaseView` (UniProtKB Card with feature annotations) | `backend/tests/test_molecular_clients.py::test_uniprot_client_get_protein` |

---

### Module 4: Secondary Molecular Databases (CO: 4)

| Database Family | Core Databases | Backend Implementation | API Endpoint | Frontend UI View | Verification & Tests |
|---|---|---|---|---|---|
| **Protein Motifs & Signatures** | **PROSITE** | `backend/utils/functional_client.py:prosite_to_regex` & `scan_motifs` (IUPAC pattern-to-regex scanner) | `POST /api/bio/motifs/scan` | `BioDatabaseView` (Interactive Motif Scanner & match coordinates viewer) | `backend/tests/test_structure_pathways_genomics.py::test_prosite_to_regex_conversion`, `test_scan_prosite_motifs` |
| **Protein Families & Domains** | **Pfam**, **InterPro** | `backend/utils/functional_client.py:get_pfam_domain` (HMM profile domain lookups) | `GET /api/bio/lookup/{query}` | `BioDatabaseView` (Annotated Domains badges) & `BioEntityCard` | `backend/tests/test_structure_pathways_genomics.py::test_unified_bio_lookup_mammoth` |

---

### Module 5: Structural Databases (CO: 4)

| Database Family | Core Databases | Backend Implementation | API Endpoint | Frontend UI View | Verification & Tests |
|---|---|---|---|---|---|
| **3D Coordinate Repositories** | **RCSB Protein Data Bank (PDB)** | `backend/utils/pdb_client.py:PdbClient` (RCSB Data API, PDB flatfile caching) | `GET /api/bio/structure/{pdb_id}`, `GET /api/bio/structure/{pdb_id}/coordinates` | `MolecularViewer.tsx` (Interactive 3D WebGL viewer with Cartoon, Stick, Sphere modes) | `backend/tests/test_structure_pathways_genomics.py::test_pdb_client_get_structure` |
| **Structural Classification** | **CATH** & **SCOP** | `backend/utils/pdb_client.py` (PDBe SIFTS fold and topology mappings) | `GET /api/bio/structure/{pdb_id}` | `BioDatabaseView` (CATH Class/Architecture/Topology and SCOP Fold badges) | `backend/tests/test_structure_pathways_genomics.py::test_pdb_client_get_structure` |
| **Paleogenomic Mutation Mapping** | Residue-level crystal structure mapping | `backend/utils/pdb_client.py:get_mutation_mapping` | `GET /api/bio/structure/{pdb_id}/mutations` | `MolecularViewer.tsx` (Highlights mutated residues on 3D structure: e.g. Mammoth `Thr12Ala`, `Ala86Ser`) | `backend/tests/test_structure_pathways_genomics.py::test_pdb_mutation_mapping` |

---

### Module 6: Specialized, Pathway & Interaction Databases (CO: 5)

| Database Family | Core Databases | Backend Implementation | API Endpoint | Frontend UI View | Verification & Tests |
|---|---|---|---|---|---|
| **Biological Pathways** | **KEGG (Kyoto Encyclopedia of Genes and Genomes)** | `backend/utils/functional_client.py:get_kegg_pathway` (KEGG REST API) | `GET /api/bio/pathways/{pathway_id}` | `BioDatabaseView` (KEGG Pathways Card with direct link to KEGG Pathway Map) | `backend/tests/test_structure_pathways_genomics.py::test_functional_client_string_and_kegg` |
| **Protein Interaction Networks** | **STRING DB** | `backend/utils/functional_client.py:get_string_interactions` (STRING API v12 with 7 evidence channels) | `GET /api/bio/interactions/{identifier}` | `BioDatabaseView` (STRING PPI Card with min combined score slider & channel breakdown) | `backend/tests/test_structure_pathways_genomics.py::test_functional_client_string_and_kegg` |
| **Genome Browsers & Loci** | **Ensembl** & **UCSC Genome Browser** | `backend/utils/genomics_client.py:GenomicsClient` (Ensembl REST coordinates & UCSC Gateway deep-links) | `GET /api/bio/locus/{gene_symbol}` | `BioDatabaseView` (Genomic Locus card with preloaded Altai Neanderthal & Denisovan tracks) | `backend/tests/test_structure_pathways_genomics.py::test_genomics_client_locus_and_ucsc_links` |

---

### Module 7: Distributed Architecture & Infrastructure (CO: 6)

| Architectural Component | Technology / Stack | Implementation File | Verification & Execution |
|---|---|---|---|
| **Microservice Orchestration** | Docker Compose v3.9 | `docker-compose.yml` (Nginx frontend, FastAPI API, Celery worker, Redis broker, Qdrant vector store, Ollama LLM) | `docker compose up --build` |
| **Web Frontend Proxy** | Nginx Alpine (Reverse Proxy & SSE stream passthrough) | `frontend/Dockerfile`, `frontend/nginx.conf` | `npm run build` (1624 modules bundled with 0 errors) |
| **Asynchronous Task Processing** | Celery + Redis | `backend/workers/celery_app.py`, `backend/workers/tasks.py` | `backend/tests/test_tasks.py` |
| **Vector Indexing Engine** | Qdrant Vector DB | `backend/storage/vector_store.py` (Cosine metric, payload filtering, RRF fusion) | `backend/tests/test_vector_store.py` |
| **Resilient External HTTP Client** | Disk caching, host throttling, exponential backoff | `backend/utils/http_client.py` (`BioHttpClient`) | `backend/tests/test_foundations.py` |

---

## Benchmark & Academic Verification Summary

- **Unit & Integration Tests**: 78 / 78 passing (`pytest backend/tests/ -v`).
- **Frontend TypeScript & Production Build**: 0 errors (`npm run check` and `npm run build`).
- **Golden Evaluation Benchmark** (`eval/run_eval.py` against 27 gold paleogenomic questions):
  - **Recall@5**: **100.00%** (27/27 golden answers retrieved in top 5).
  - **Citation Faithfulness**: **96.30%** (26/27 answers strictly grounded in retrieved evidence).
- **Academic Rigor**: All biological database accessions verified against live primary resources (documented in `docs/DISCREPANCIES.md`).
