# PaleoRAG: Phylogenetic Context Engine & Biological Databases Platform

PaleoRAG is a unified bioinformatics platform and citation-grounded Retrieval-Augmented Generation (RAG) system tailored for paleogenomics, evolutionary biology, and molecular database mining. It integrates primary sequence repositories (NCBI GenBank, EMBL-EBI ENA, DDBJ), protein annotation resources (UniProtKB, PIR), macromolecular structural databases (RCSB PDB, CATH, SCOP), functional domain profiles (Pfam, PROSITE), metabolic pathways (KEGG), protein-protein interaction networks (STRING), and comparative genome browsers (Ensembl, UCSC) into an interactive dual-pane research environment.

The platform directly implements and validates all 7 modules of the **Biological Databases Coursework Syllabus (CO1–CO6)**.

---

## Architecture Overview

```
                      +-----------------------------------------------------+
                      |             PaleoRAG Frontend (React 19)            |
                      |  - Research Studio (Dual-Pane Grounding + Citations)|
                      |  - Sequence Workbench (Validation, Formats, Dogma)  |
                      |  - BioDB Explorer (3Dmol WebGL, PPI Networks, KEGG) |
                      +--------------------------+--------------------------+
                                                 | (HTTP REST / SSE Stream)
                                                 v
                      +-----------------------------------------------------+
                      |            FastAPI Orchestration Gateway             |
                      |  - /api/chat/stream (SSE Tokens + BioEntity Cards)  |
                      |  - /api/bio/* (Sequence Tools & DB Aggregator)      |
                      |  - /api/health (Distributed Service Diagnostics)    |
                      +-------+--------------------+-------------------+----+
                              |                    |                   |
            +-----------------+                    |                   +-----------------+
            v                                      v                                     v
+-----------------------+              +-----------------------+              +-----------------------+
|  Hybrid RAG Engine    |              | Molecular DB Pipeline |              |   Sequence Workbench  |
| - PubMedBERT (768d)   |              | - NCBI GenBank (Entrez|              | - IUPAC Validation    |
| - In-Memory BM25Okapi |              | - ENA / DDBJ Browser  |              | - Biopython Converter |
| - RRF Fusion (k=60)   |              | - UniProtKB / PIR     |              |   (FASTA/GBK/EMBL)    |
| - GBIF / PBDB Taxonomy|              | - RCSB PDB & CATH/SCOP|              | - Central Dogma 6-Fr  |
| - Citation Auditor    |              | - Pfam & PROSITE Scan |              | - INSDC Submission    |
+-----------+-----------+              | - KEGG & STRING Net   |              +-----------------------+
            |                          | - Ensembl & UCSC Tracks              
            v                          +-----------+-----------+
+-----------------------+                          |
|  Vector & Cache Tier  |                          v
| - Qdrant Vector Store |              +-----------------------+
| - Redis Broker/Cache  |              | Distributed Workers   |
| - Local DiskCache     |              | - Celery Async Queue  |
+-----------------------+              | - Ollama LLM Service  |
                                       +-----------------------+
```

---

## Coursework Syllabus Alignment (CO1 – CO6)

PaleoRAG provides full, verifiable implementation of the 7-module coursework syllabus:

| Module & Topic | Syllabus Focus | Implementation in PaleoRAG |
|---|---|---|
| **Module 1: Sequence Submission Tools (CO1)** | IUPAC validation, sequence formats, Central Dogma, sequence interconversion, submission checklist. | `SequenceWorkbenchView`: IUPAC validator, Biopython bidirectional converter (`FASTA` $\leftrightarrow$ `GenBank` $\leftrightarrow$ `EMBL`), 6-frame translation and ORF detector, INSDC submission metadata validator. |
| **Module 2: Biological Data Integration & Mining (CO2)** | Multi-database integration, cross-domain mining, AI in data integration, challenges in integration. | `BioAggregator`: federated multi-database querying; Hybrid dense+sparse RAG with PubMedBERT and Reciprocal Rank Fusion ($k=60$); dual-pane grounded `BioEntityCard`. |
| **Module 3: Primary Molecular Databases (CO3)** | INSDC collaboration (NCBI GenBank, ENA, DDBJ); UniProtKB (Swiss-Prot, TrEMBL); PIR legacy cross-references. | `ncbi_client.py` (E-utilities), `ena_ddbj_client.py` (ENA Browser API), `uniprot_client.py` (UniProt REST API with active sites, PTMs, disulfides, PIR cross-refs). |
| **Module 4: Secondary Molecular Databases (CO4)** | Protein motifs and domains (PROSITE pattern matching, Pfam HMM profiles, InterPro). | `functional_client.py`: offline-capable PROSITE IUPAC regex scanner (`prosite_to_regex`), Pfam domain family lookups via InterPro. |
| **Module 5: Structural Databases (CO4)** | RCSB PDB 3D coordinates, structural classifications (CATH, SCOP), paleogenomic mutation mapping. | `pdb_client.py` & `MolecularViewer.tsx`: RCSB PDB fetcher, PDBe SIFTS fold mappings (CATH architecture, SCOP fold), interactive WebGL 3Dmol viewer, mutation residue mapping. |
| **Module 6: Specialized & Pathway Databases (CO5)** | KEGG pathways, STRING protein interaction networks, Ensembl & UCSC Genome Browser tracks. | `functional_client.py` & `genomics_client.py`: KEGG REST pathway maps, STRING DB PPI networks with 7 evidence channels, Ensembl locus coordinates, and UCSC archaic tracks (Altai Neanderthal, Denisovan). |
| **Module 7: Distributed Architecture (CO6)** | Multi-container microservices, asynchronous task queues, resilient HTTP clients with rate-limiting. | Multi-stage Docker Compose (Nginx, FastAPI, Celery, Redis, Qdrant, Ollama), disk caching, host rate limiters, exponential backoff retries. |

*For complete mapping details, see [docs/SYLLABUS_MAP.md](docs/SYLLABUS_MAP.md).*

---

## Verified Paleogenomic Case Studies

PaleoRAG includes pre-configured, peer-reviewed case studies linking literature, sequences, structures, pathways, and mutations:

### 1. Woolly Mammoth Cold-Adapted Hemoglobin (*Mammuthus primigenius*)
- **Primary Nucleotide**: GenBank `HQ184444.1` (1060 bp)
- **UniProtKB Accession**: `D3U1H9` (`HBB_MAMPR`, 147 aa)
- **RCSB PDB Structure**: `3VRF` (1.55 Å resolution, X-ray diffraction)
- **Folds & Domains**: CATH `1.10.490.10` (Globin-like), Pfam `PF00042`, PROSITE `PS01033`
- **Mutations Mapped**: $\beta 12\text{Thr} \rightarrow \text{Ala}$, $\beta 86\text{Ala} \rightarrow \text{Ser}$, $\beta 101\text{Glu} \rightarrow \text{Gln}$ (alters allosteric oxygen affinity and reduces heat enthalpy of oxygenation in arctic climates).

### 2. Neanderthal Speech-Associated Transcription Factor (*Homo neanderthalensis*)
- **Primary Nucleotide**: GenBank `AF512946.1` (2148 bp)
- **UniProtKB Accession**: `O15409` (`FOXP2_HUMAN` / archaic hominin identical sequence, 715 aa)
- **RCSB PDB Structure**: `2A07` (Forkhead-DNA crystal complex)
- **Folds & Domains**: CATH `1.10.10.10` (Winged helix), Pfam `PF00250`, PROSITE `PS00658` (`FORK_HEAD_2` pattern)
- **Genomic Locus**: Chromosome 7q31.1 (`chr7:114086327-114693768`), UCSC Altai Neanderthal / Denisovan archaic tracks.

### 3. Ancient *Yersinia pestis* Plasminogen Activator (*pPCP1 Pla Protease*)
- **Primary Nucleotide**: GenBank `AL590842.1` (9609 bp pPCP1 virulence plasmid)
- **UniProtKB Accession**: `P17811` (`PLA_YERPE`, 312 aa)
- **RCSB PDB Structure**: `2X55` (1.85 Å resolution, 10-stranded $\beta$-barrel omptin protease)
- **Folds & Domains**: CATH `2.40.40.10` (Outer membrane protein), Pfam `PF01278` (Omptin family), PROSITE `PS00834`
- **Pathways & Interactions**: KEGG `map05100` (Bacterial invasion of epithelial cells), STRING DB interaction network with outer membrane proteins and plasminogen substrates.

*For accession corrections from preliminary literature, see [docs/DISCREPANCIES.md](docs/DISCREPANCIES.md).*

---

## Evaluation Benchmark & Verification

The platform was verified using automated unit testing and the golden evaluation benchmark:

| Metric | Result | Description |
|---|---|---|
| **Retrieval Recall@5** | **100.00%** | 27 / 27 golden questions retrieved expected scientific literature |
| **Citation Faithfulness** | **96.30%** | 26 / 27 answers strictly grounded in retrieved passages |
| **Backend Unit & Integration Tests** | **78 / 78 Passing (100%)** | Full coverage across foundational, sequence, molecular, and RAG modules |
| **Frontend TypeScript & Build** | **0 Errors** | 1,624 modules transformed into optimized production bundle |

---

## Quickstart Guide

### 1. Local Environment Setup

```bash
# 1. Clone repository
git clone <repository-url>
cd paleo_rag

# 2. Setup Python environment
python -m venv .venv
# On Windows:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# 3. Install backend dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Copy environment settings
cp .env.example .env
```

### 2. Launching the Backend

```bash
# Run local FastAPI server with auto-reload
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation is accessible at `http://localhost:8000/docs`.

### 3. Launching the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` to interact with:
- **Research Studio**: Conversational RAG with live token streaming and dual-pane `BioEntityCard` grounding.
- **Sequence Workbench**: IUPAC validator, format converter (FASTA/GBK/EMBL), 6-frame translation and ORF detector, INSDC submission validator.
- **BioDB Explorer**: Multi-database queries, case study presets, WebGL 3D molecular viewer with mutation mapping, and STRING interaction networks.

### 4. Containerized Multi-Service Deployment (Docker Compose)

```bash
# Launch entire distributed microservice stack (Frontend, Backend, Celery, Redis, Qdrant, Ollama)
docker compose up --build -d

# Pull local LLM model inside Ollama container
docker compose exec ollama ollama pull llama3.2:1b
```

---

## Running Automated Tests & Benchmark

```bash
# Run backend pytest suite (all 78 tests)
pytest backend/tests/ -v

# Run golden benchmark evaluation with embedding comparison
python eval/run_eval.py --golden-set eval/golden_set.jsonl --compare-embeddings

# Verify frontend TypeScript types
cd frontend && npm run check
```

---

## License

This project is licensed under the MIT License. Ingested literature and database records adhere to their respective open-access terms (CC-BY 4.0, INSDC Open Data Policies, RCSB PDB, and UniProt Open Access).
