# REPO_AUDIT.md — Comprehensive Repository Architecture & Legacy Data Audit

**Date**: 2026-10-13  
**Auditor**: Antigravity Agent  
**Environment**: Windows 11 (Build 26200), Python 3.11.9, Node v22.14.0, Vite 7.3.6  
**Git Baseline Commit**: `e7c86bc946f9f27af7e9372683d24276d6a0d303`  
**Baseline Test Suite**: 99 / 99 passed (100%) in 123.72s  
**Baseline Frontend Build**: `tsc --noEmit` clean (0 errors), `vite build` clean (2032 modules transformed in 9.45s)  

---

## 1. Stack Architecture & Entry Points

### 1.1 Backend Stack
- **Framework**: FastAPI 0.141.1 (`backend/main.py:14`), Starlette 1.6.0, Uvicorn 0.52.4.
- **Async Task Processing**: Celery 5.6.3 (`backend/workers/celery_app.py:10`), Redis 8.1.0 (`backend/config.py:22-24`).
- **Data Schemas & Settings**: Pydantic 2.13.5 (`backend/api/schemas.py`, `backend/api/bio_schemas.py`), Pydantic Settings 2.15.0 (`backend/config.py:13-96`).
- **Computational Biology**: Biopython 1.84 (`backend/utils/sequence_tools.py:10-12`).
- **PDF & Document Parsing**: PyMuPDF 1.28.2 (`backend/utils/pdf_parser.py:15`), Python standard `xml.etree.ElementTree` (`backend/utils/pdf_parser.py:13`).
- **Vector & Lexical Search**: Qdrant Client 1.19.0 (`backend/core/vector_store.py:24`), `rank-bm25` 0.2.2 (`backend/core/rag_pipeline.py:34`).
- **Embeddings & ML**: PyTorch 2.14.0, Transformers 4.57.6, Sentence-Transformers 3.2.1 (`backend/core/embeddings.py:20`). Active model: `NeuML/pubmedbert-base-embeddings` (768-d).
- **LLM Clients**: Ollama HTTP API (`backend/core/llm_client.py:48`), Anthropic SDK 0.39.0 (`backend/core/llm_client.py:90`), Mock client for offline testing (`backend/core/llm_client.py:22`).
- **HTTP Client**: Centralized `BioHttpClient` (`backend/utils/http_client.py:45`) with host-based rate limiting, disk caching (`DiskCache` at `./data/bio_cache`), and exponential backoff retries.

### 1.2 Frontend Stack
- **Framework**: React 19.3.0, ReactDOM 19.3.0 (`frontend/package.json:51-53`).
- **Language**: TypeScript 5.6.3 (`frontend/tsconfig.json`).
- **Build Tool / Bundler**: Vite 7.3.6 with `@vitejs/plugin-react` 5.2.0 (`frontend/vite.config.ts:4-31`).
- **Styling**: Tailwind CSS v4.3.3 with `@tailwindcss/vite` 4.3.3 (`frontend/vite.config.ts:1-7`).
- **UI Components**: Radix UI primitives (`@radix-ui/react-tabs`, `accordion`, `dialog`, `dropdown-menu`, `popover`, `tooltip`, etc.), Lucide React icons 0.453.0.
- **Routing**: Wouter 3.11.0 (`frontend/client/src/App.tsx`).
- **Molecular 3D Rendering**: 3Dmol.js (WebGL embedded script) (`frontend/client/src/components/MolecularViewer.tsx:40-70`).

---

## 2. Current Data Storage Format

The repository currently uses file-based storage across multiple directories:

1. **Species Registry & Protein Data**:
   - `backend/data/paleo_atlas_registry.json` (391,350 bytes): JSON array of 18 codified taxa records containing embedded loci, molecular samples, fossil metadata, and ecological profiles.
   - `frontend/client/src/lib/paleo_atlas_registry.json` (391,350 bytes): Identical copy bundled into the frontend build for client-side fallback.
   - `backend/data/preindexed_case_studies.json` (470,479 bytes): JSON dictionary of 104 search keys/aliases mapping to pre-computed molecular database records.
   - `frontend/client/src/lib/preindexed_case_studies.json` (470,479 bytes): Identical copy for client fallback.
   - `frontend/client/src/lib/taxa_literature.json` (55,722 bytes): Pre-compiled JSON bundle of 18 taxa publication summaries and abstracts.

2. **Literature & Document Corpus**:
   - `data/processed/manifest.jsonl` (25,351 bytes): JSON Lines file containing metadata (`doc_id`, `source`, `license`, `doi`, `title`, `raw_path`, `status`) for 26 ingested documents.
   - `data/raw_pdfs/` (32 files, ~26 MB): Downloaded PMC full-text XML files (`PMC*.xml`) and bioRxiv PDF preprints.

3. **Vector Database**:
   - `data/qdrant_storage/`: Local embedded Qdrant database files (`storage.sqlite`, collection `paleo_chunks`, 768-d Cosine vectors).

4. **HTTP Cache**:
   - `data/bio_cache/`: Key-value cache files stored on disk by `BioHttpClient` and audit scripts.

5. **Legacy Archive (Phase P0 Baseline)**:
   - `archive/legacy_20261013/`: Complete baseline snapshot containing 76 files with verified `manifest.json` (SHA-256 hashed).

---

## 3. Storage Architecture for Taxa, Protein Records, and Structure Mappings

In the legacy architecture:
1. **Taxon Level (`backend/data/paleo_atlas_registry.json`)**:
   - Each taxon entry has fields: `tax_id` (e.g. `PRAG-TAX-001`), `common_name`, `scientific_name`, `clade`, `epoch`, `extinction_date`, `key_trait`, `description`, `image_url`, `image_caption`, `habitat_range`, `geological_range`, `diet_ecology`, `morphology`, `extinction_driver`.
   - **NCBI Taxonomy ID**: Currently NOT explicitly stored as a top-level typed integer. `tax_id` is an internal project code (`PRAG-TAX-001` through `PRAG-TAX-018`).
2. **Target Locus & Molecular Samples**:
   - `target_locus`: A single primary marker object containing `gene_symbol`, `protein_name`, `extinct_uniprot_acc`, `extinct_nucleotide_acc`, `extinct_sequence_aa`, `extinct_sequence_dna`.
   - `molecular_samples`: An array of 3 to 4 samples per taxon (total 68 samples across the 18 taxa). Each sample contains: `sample_id`, `gene_symbol`, `protein_name`, `category`, `biological_significance`, `extinct_uniprot_acc`, `extinct_nucleotide_acc`, `extinct_sequence_aa`, `extinct_uniprot_validation`, `extant_counterpart`, `structure`, `genomics`, `pathway`.
3. **PDB Structure Mapping**:
   - Embedded directly as an object inside each sample: `structure: { pdb_id: str, title: str, method: str, resolution: float, mutations: [...] }`.
   - Structures are mapped 1:1 per sample. There is **no one-to-many structure mapping** supported in the legacy schema; alternative conformations or chains cannot be linked to a single protein.
4. **Cross-References**:
   - `genomics`: Embedded `{ chromosome, start, end, assembly, ensembl_species }`.
   - `pathway`: Embedded `{ kegg_id, pathway_name, description }`.
   - No structured foreign keys or relational tables exist; all data is serialized into deeply nested JSON trees.

---

## 4. How the UI Reads Data

- **Primary Atlas Loading (`frontend/client/src/lib/api.ts:960-984`)**:
  - The frontend calls `fetchAtlas()`, which makes a `GET /api/bio/atlas` request to the FastAPI backend.
  - If the backend call succeeds, the returned JSON array is stored in React state (`TaxaAtlasView.tsx:68-71`).
  - If the backend is unavailable or returns an error, `fetchAtlas()` silently falls back to reading the bundled static file `atlasRegistryData` from `frontend/client/src/lib/paleo_atlas_registry.json:973-983`.
- **Taxon Detail View (`frontend/client/src/components/TaxaAtlasView.tsx:133-153`)**:
  - When a user clicks a taxon card, the component inspects `viewingTaxon.molecular_samples`.
  - The user can toggle between the 3–4 samples using a sample pill selector (`TaxaAtlasView.tsx:470-510`).
  - Selecting a sample sets `activeSample`, which drives the overview card, comparative alignment matrix, 3D structure viewer, and genomic locus coordinates.

---

## 5. How the RAG Pipeline Ingests and Answers

### 5.1 Ingestion Flow (`backend/workers/tasks.py:18-120`)
1. User uploads a PDF/XML via `/api/upload` (`backend/api/routes.py:35`) or triggers ingestion via `/api/ingest` (`routes.py:67`).
2. Document is saved to `data/raw_pdfs/` and queued in `data/processed/manifest.jsonl`.
3. Celery task chain executes:
   - `extract_document_metadata`: Reads title, doi, PMC ID, license from file.
   - `parse_document`: `backend/utils/pdf_parser.py` extracts text blocks, structured tables, and figure captions.
   - `chunk_document`: `backend/core/chunking.py` splits text into section-aware chunks (~512 tokens, 50 overlap, 1024 hard cap) with SHA-256 content hashes.
   - `embed_chunks`: `backend/core/embeddings.py` computes 768-d PubMedBERT dense vectors in batches of 32.
   - `upsert_chunks`: `backend/core/vector_store.py` inserts chunks into Qdrant using deterministic UUID5 point IDs: `_to_qdrant_point_id("{doc_id}::{chunk_index}")`.

### 5.2 Retrieval & Generation Flow (`backend/api/routes.py:172-252`, `backend/core/rag_pipeline.py:180-280`)
1. User sends a query to `POST /api/chat/stream`.
2. `query_expansion`: If enabled, `TaxonomyClient` (`backend/utils/taxonomy_client.py:40`) extracts taxon entities via GBIF Backbone / PBDB and adds scientific binomens to query terms.
3. `hybrid_search`: `VectorStore.hybrid_search()` runs dense search in Qdrant and sparse lexical search via in-process `BM25SparseIndex` (`rank_bm25`). Rank fusion is performed using Reciprocal Rank Fusion ($k=60$).
4. Top 8 chunks are retrieved and formatted into `PROMPT_TEMPLATE` with marker syntax `[doc_id:chunk_index]`.
5. Streaming generation is performed via Ollama (or Anthropic / Mock).
6. Post-generation citation audit: `check_citations()` scans output for `[doc_id:chunk_index]` regex and flags ungrounded citations.
7. Terminal SSE event emits retrieved evidence chunks and linked `BioEntityCard` records.

---

## 6. What "Literature Corpus" and "Telemetry" Tabs Currently Show

### 6.1 Literature Corpus Tab (`frontend/client/src/pages/Home.tsx:1450-1650`)
- **Document Table**:
  - Displays list of documents fetched from `GET /api/documents` (or fallback `DEFAULT_CORPUS`).
  - Columns: PMC/Doc ID, Paper Title, Publication Year, Associated Taxon, License Tag, Ingestion Status ("Indexed" / "Queued").
- **Ingestion Controls**:
  - Drag-and-drop / file upload modal calling `/api/upload`.
  - Remote ingestion modal allowing input of PMC ID or bioRxiv DOI calling `/api/ingest`.
- **Live Task Tracker**:
  - Displays queued/running Celery ingestion tasks polled via `GET /api/task/{task_id}` with status badges (`QUEUED`, `STARTED`, `SUCCESS`, `FAILURE`).

### 6.2 System Telemetry Tab (`frontend/client/src/pages/Home.tsx:1850-2015`)
- **Distributed Health Status**:
  - Fetched from `GET /api/health`.
  - Indicators for Qdrant Vector DB, Redis broker, Celery worker process, and LLM provider connectivity.
- **Runtime Environment Settings**:
  - Displays active backend configuration: `API_HOST`, `API_PORT`, `EMBEDDING_MODEL_NAME` (`NeuML/pubmedbert-base-embeddings`), `EMBEDDING_DIMENSION` (768), `QDRANT_COLLECTION_NAME` (`paleo_chunks`), `SPARSE_RETRIEVAL_BACKEND` (`rank_bm25`), `LLM_PROVIDER` (`ollama`), `OLLAMA_MODEL` (`llama3.2:1b`).
- **Telemetry Counters**:
  - Displays session query count, active task queue size, vector collection point count, and disk cache hit rate.

---

## 7. How PaleoBioDB Links are Built

- **In Data Generation (`scripts/enrich_atlas_with_pbdb.py:8-100`)**:
  - Script hardcodes `pbdb_navigator_url = "https://paleobiodb.org/navigator/"` and `pbdb_api_url = "https://paleobiodb.org/data1.2/occs/list.json?base_name={scientific_name}"`.
- **In Frontend UI (`frontend/client/src/components/TaxaAtlasView.tsx:423-433`, line 930)**:
  - Renders an anchor tag: `<a href={t.fossil_record.pbdb_navigator_url} target="_blank" rel="noreferrer">Navigator</a>`.
  - The URL is simply the generic root of the PBDB Navigator map tool, without taxon query parameters.
- **Identified PBDB 403 / Navigation Problem**:
  - Live API testing confirmed that server-side requests to `https://paleobiodb.org/data1.2/taxa/single.json` and `https://paleobiodb.org/navigator/` return `200 OK` when accessed with standard HTTP clients.
  - However, direct links to `https://paleobiodb.org/navigator/` do not open a specific taxon's page; the authoritative PBDB taxon info page is `https://paleobiodb.org/classic/checkTaxonInfo?taxon_no={taxon_no}`. Furthermore, client-side browser fetches directly to PBDB API without a proxy trigger CORS or rate/security blocks (often resulting in 403 Forbidden).

---

## 8. How the Synteny Tab Computes Its Data

In `frontend/client/src/components/TaxaAtlasView.tsx:156-200` and lines 638–740:
1. **Raw Residue String Extraction**:
   - Reads `extinct = activeSample.extinct_sequence_aa` and `extant = activeSample.extant_counterpart.extant_sequence_aa`.
2. **In-Browser String Loop Comparison (Lines 186-200)**:
   - Iterates character-by-character from `0` to `max(extinct.length, extant.length)`.
   - Evaluates `extinct[i] == extant[i]`. If characters match, increments `matches`. If different and neither is `-`, increments `substitutions`.
   - Computes sequence identity: `identityPct = round((matches / minLen) * 100)`.
   - Computes divergence: `divergencePct = round((substitutions / minLen) * 100)`.
3. **Approximated Grantham Distance (Lines 176-184)**:
   - Uses a hardcoded JavaScript lookup table for a few residue pairs (`TA: 58, AS: 99, EQ: 29, RG: 125...`) with a default fallback of `45`.
4. **Architectural Gaps & Plan Violations**:
   - **No genuine pairwise sequence alignment**: String indexing assumes identical coordinate offsets and no insertion/deletion gaps.
   - **Client-side computation**: Scoring and alignment are executed directly inside the React browser thread.
   - **No true genomic synteny**: The tab is named "Extant Relative Synteny", but it computes an unaligned amino acid identity percentage. It does not inspect genomic coordinates, ortholog gene neighborhoods, or chromosomal synteny blocks.

---

## 9. Legacy Field Inventory (UI Dependencies)

Every field accessed across the frontend UI components from legacy data is cataloged below to ensure complete continuity during the Phase P3–P8 data rebuild:

| Entity / Object | Field Name | Type | Accessed By | UI Role / Purpose |
|---|---|---|---|---|
| **Taxon** | `tax_id` | `string` | `TaxaAtlasView.tsx`, `api.ts` | Taxon identifier & selection key (e.g. `PRAG-TAX-001`) |
| **Taxon** | `common_name` | `string` | `TaxaAtlasView.tsx`, `Home.tsx` | Primary heading & filter term (e.g. "Woolly Mammoth") |
| **Taxon** | `scientific_name` | `string` | `TaxaAtlasView.tsx`, `Home.tsx` | Italic binomen heading & search term |
| **Taxon** | `clade` | `string` | `TaxaAtlasView.tsx` | Clade filter bar (Mammalia, Aves, Carnivora, etc.) |
| **Taxon** | `epoch` | `string` | `TaxaAtlasView.tsx` | Epoch filter bar (Pleistocene, Holocene, etc.) |
| **Taxon** | `extinction_date` | `string` | `TaxaAtlasView.tsx` | Card metadata badge (e.g. "~4,000 BP") |
| **Taxon** | `key_trait` | `string` | `TaxaAtlasView.tsx` | Highlight summary badge on card |
| **Taxon** | `description` | `string` | `TaxaAtlasView.tsx` | Taxon biological overview paragraph |
| **Taxon** | `image_url` | `string` | `TaxaAtlasView.tsx` | Life reconstruction illustration image |
| **Taxon** | `image_caption` | `string` | `TaxaAtlasView.tsx` | Life reconstruction attribution & caption |
| **Taxon** | `habitat_range` | `string` | `TaxaAtlasView.tsx` | Animal dossier: paleoecological habitat profile |
| **Taxon** | `geological_range` | `string` | `TaxaAtlasView.tsx` | Animal dossier: stratigraphic range |
| **Taxon** | `diet_ecology` | `string` | `TaxaAtlasView.tsx` | Animal dossier: dietary niche & trophic role |
| **Taxon** | `morphology` | `string` | `TaxaAtlasView.tsx` | Animal dossier: anatomical measurements & adaptations |
| **Taxon** | `extinction_driver` | `string` | `TaxaAtlasView.tsx` | Animal dossier: hypothesized extinction drivers |
| **Taxon.fossil_record** | `pbdb_taxon_id` | `string \| null` | `TaxaAtlasView.tsx` | Fossil record badge & PBDB identifier |
| **Taxon.fossil_record** | `pbdb_taxon_name` | `string \| null` | `TaxaAtlasView.tsx` | PBDB verified scientific name |
| **Taxon.fossil_record** | `pbdb_navigator_url` | `string` | `TaxaAtlasView.tsx` | External link to Paleobiology Database |
| **Taxon.fossil_record** | `fossil_occurrences_count` | `number \| null`| `TaxaAtlasView.tsx` | Count of cataloged fossil collections |
| **Taxon.fossil_record** | `first_appearance_ma` | `number \| null`| `TaxaAtlasView.tsx` | First appearance datum (Ma) |
| **Taxon.fossil_record** | `last_appearance_ma` | `number \| null`| `TaxaAtlasView.tsx` | Last appearance datum (Ma) |
| **Taxon.fossil_record** | `geological_interval` | `string` | `TaxaAtlasView.tsx` | Stratigraphic interval text |
| **Taxon.publications** | `pmcid` / `doi` | `string` | `TaxaAtlasView.tsx` | Publication identifier links |
| **Taxon.publications** | `title` / `year` / `journal` | `string` / `number` | `TaxaAtlasView.tsx` | Paper citation metadata strip |
| **Protein / Sample** | `sample_id` | `string` | `TaxaAtlasView.tsx` | Unique sample ID (e.g. `PRAG-TAX-001-SMP-01`) |
| **Protein / Sample** | `gene_symbol` | `string` | `TaxaAtlasView.tsx`, `BioDatabaseView.tsx` | Official gene symbol (e.g. `HBB`, `FOXP2`) |
| **Protein / Sample** | `protein_name` | `string` | `TaxaAtlasView.tsx`, `BioDatabaseView.tsx` | Full protein name (e.g. "Hemoglobin subunit beta") |
| **Protein / Sample** | `category` | `string` | `TaxaAtlasView.tsx` | Locus category ("Primary Diagnostic Marker", etc.) |
| **Protein / Sample** | `biological_significance` | `string` | `TaxaAtlasView.tsx` | Adaptive significance explanation |
| **Protein / Sample** | `extinct_uniprot_acc` | `string \| null` | `TaxaAtlasView.tsx`, `BioDatabaseView.tsx` | UniProt accession for extinct taxon |
| **Protein / Sample** | `extinct_uniprot_validation` | `object \| null` | `TaxaAtlasView.tsx` | Provenance note & verification status |
| **Protein / Sample** | `extinct_nucleotide_acc` | `string` | `TaxaAtlasView.tsx` | GenBank nucleotide accession (e.g. `HQ184444.1`) |
| **Protein / Sample** | `extinct_sequence_aa` | `string` | `TaxaAtlasView.tsx` | Full amino acid sequence for extinct protein |
| **Protein / Sample** | `extinct_sequence_dna` | `string` | `TaxaAtlasView.tsx` | Full CDS nucleotide sequence (target_locus) |
| **Sample.extant** | `common_name` / `scientific_name`| `string` | `TaxaAtlasView.tsx` | Living sister taxon names (e.g. *Elephas maximus*) |
| **Sample.extant** | `extant_uniprot_acc` | `string \| null` | `TaxaAtlasView.tsx` | Modern sister taxon UniProt accession |
| **Sample.extant** | `extant_nucleotide_acc`| `string` | `TaxaAtlasView.tsx` | Modern sister taxon nucleotide accession |
| **Sample.extant** | `extant_sequence_aa` | `string` | `TaxaAtlasView.tsx` | Modern sister taxon protein sequence |
| **Sample.structure** | `pdb_id` | `string` | `TaxaAtlasView.tsx`, `MolecularViewer.tsx` | RCSB PDB 4-character structure ID |
| **Sample.structure** | `title` / `method` / `resolution` | `string` / `number` | `TaxaAtlasView.tsx` | Structural experiment metadata |
| **Sample.structure** | `mutations` | `array` | `TaxaAtlasView.tsx`, `MolecularViewer.tsx` | Amino acid substitutions mapped onto 3D structure |
| **Sample.genomics** | `chromosome` / `start` / `end` | `string` / `number` | `TaxaAtlasView.tsx` | Genomic locus coordinates |
| **Sample.genomics** | `assembly` / `ensembl_species` | `string` | `TaxaAtlasView.tsx` | Genome reference assembly & Ensembl link |
| **Sample.pathway** | `kegg_id` / `pathway_name` | `string` | `TaxaAtlasView.tsx` | KEGG pathway identifier & map name |

---

## 10. Empirical Legacy Error Quantification (Phase P0 Addition 1)

### 10.1 Methodology & Sampling
- **Population**: All 172 protein accession sites across all 18 taxa in `backend/data/paleo_atlas_registry.json`.
- **Sampling**: Random sample of 100 records drawn with fixed pseudo-random seed `seed = 42`.
- **Live APIs Queried**:
  - UniProtKB REST API (`https://rest.uniprot.org/uniprotkb/{acc}.json`)
  - RCSB PDB REST API (`https://data.rcsb.org/rest/v1/core/entry/{pdb_id}` and `/core/polymer_entity/{pdb_id}/1`)
- **Raw Data Log**: Persisted to `docs/verification/legacy_error_audit_sample100_seed42.json` with SHA-256 cache hashes.

### 10.2 Empirical Verification Results
| Metric / Check | Measured Count | Percentage of Sample ($n=100$) | Finding & Significance |
|---|---|---|---|
| **Total Sampled Records** | 100 | 100.0% | Representative cross-section of all 18 taxa |
| **UniProt Accession Populated** | 42 | 42.0% | Only 42% had any UniProt accession |
| **UniProt Accession Null / Unmapped** | 58 | 58.0% | **58% of legacy records lacked UniProt mapping** |
| **Populated Accessions Resolving (HTTP 200)** | 42 / 42 | 100.0% | All populated accessions are real UniProt IDs |
| **UniProt Organism Exact Match** | 40 / 42 | 95.2% | Matches target organism |
| **UniProt Organism Mismatch** | 2 / 42 | 4.8% | Organism mismatch in populated accession |
| **PDB Structure ID Present** | 50 | 50.0% | 50 records claimed an associated PDB structure |
| **PDB Structure Resolving (HTTP 200)** | 50 / 50 | 100.0% | All 50 PDB IDs exist in RCSB PDB |
| **PDB Structure Organism Matches Taxon** | 6 / 50 | 12.0% | Only 6 structures actually derived from target taxon |
| **PDB Structure Organism Mismatch** | **44 / 50** | **88.0%** | **88% of PDB links attached modern or human structures to extinct taxa** |
| **PDB Entry Contains Claimed UniProt Protein** | 2 / 50 | 4.0% | Only 2 structures contained the claimed UniProt accession |
| **PDB Entry Lacks Claimed UniProt Protein** | **48 / 50** | **96.0%** | **96% of PDB links did not contain the linked protein** |

### 10.3 Summary of Legacy Failure Modes
1. **Pervasive Organism Misattribution in Structural Links**: 88% of structure links in the sample used homologous human, bovine, or rodent structures without flagging them as proxies or homologs.
2. **Missing Authoritative Mappings**: 58% of protein sites had no UniProt accession, leaving them unanchored to primary databases.
3. **PDB-to-UniProt Disconnection**: In 96% of sampled structural links, the PDB entry did not contain the claimed UniProt protein entity.
4. **Conclusion**: This empirical audit decisively proves the necessity of the complete data rebuild mandated by `PALEORAG_PATCH_PLAN.md`.

---

## 11. Unknowns & Open Questions Identified
1. **Taxa Definition (H1)**: The repo currently codifies 18 prehistoric taxa in `paleo_atlas_registry.json`. Is this list the authoritative scope for the rebuild? (Logged as H1).
2. **UniProt Taxonomy Scope (H2)**: Should UniProt queries match exact NCBI taxon ID or include subspecies/strain descendants? (Logged as H2).
3. **UniProt Review Status (H3)**: Should we pull Swiss-Prot only, or Swiss-Prot + TrEMBL? (Logged as H3).
4. **Relational DB Architecture (H6)**: RDBMS vs SQLite vs validated files must be resolved in Phase P1 based on empirical query and volume measurements.
