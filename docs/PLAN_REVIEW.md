# PLAN_REVIEW.md — Comprehensive Plan Review & Repo Reconciliation

**Date**: 2026-10-13  
**Phase**: P1 — Plan Review and RDBMS Decision Gate  
**Auditor**: Antigravity Agent  
**Context**: Reconciling `PALEORAG_PATCH_PLAN.md` with the existing PaleoRAG codebase.

---

## 1. Plan Review & Conflict Analysis

| # | Plan Item / Requirement | Repo Current State | Identified Conflict / Risk | Proposed Resolution |
|---|---|---|---|---|
| **1** | **Taxa scope & list (H1)** | 18 taxa in `backend/data/paleo_atlas_registry.json`. | Discrepancies in NCBI rank (e.g. Neanderthal is subspecies `63221`, Denisovan is subspecies `741158`, Toxodon is genus `1563121`). | User confirmed keeping 18 taxa. Resolved NCBI Taxon IDs mapped exactly with recorded rank in `taxa` registry. |
| **2** | **UniProt scope (H2/H3)** | Legacy data used a mix of unverified accessions and proxies. | Full proteome download on viral species (*Influenza A*, 33k entries) or bacterial species (*Y. pestis*, 9.7k entries) would dwarf extinct paleogenomes. | User confirmed pulling both Swiss-Prot and TrEMBL with source indicator (`reviewed` flag). Microbial entries will focus on documented historical/ancient loci to keep scope relevant. |
| **3** | **UniProt ↔ PDB mapping (P4)** | Legacy data hardcoded single PDB IDs inside `molecular_samples` with 88% organism mismatch. | One protein $\rightarrow$ multiple PDB structures (1:N) cannot fit in the legacy nested dictionary schema without duplicating sample nodes. | Implement relational structure mapping table (`protein_structure_map`) supporting 1:N structures per protein with residue ranges from SIFTS. |
| **4** | **Extant Relative Synteny (P8)** | Naive character equality loop over unaligned strings in `TaxaAtlasView.tsx:156-200`. | Not true synteny, lacking genomic coordinates, chromosomal assembly, or verified orthology. | Replace in-browser string matching with pre-computed Ensembl Compara / OrthoDB orthology links and genomic locus coordinates (`checked_not_found` when extinct coordinates unavailable). |
| **5** | **PaleoBioDB 403 & Links (P9.3)** | Hardcoded `https://paleobiodb.org/navigator/` root in `scripts/enrich_atlas_with_pbdb.py`. | Navigator root does not deep-link to the taxon, and client-side fetches directly to PBDB trigger CORS/403. | Use verified PBDB taxon URL `https://paleobiodb.org/classic/checkTaxonInfo?taxon_no={id}` for UI links, and proxy API calls server-side with polite User-Agent and caching. |
| **6** | **Diagnostics Tab Merge (P9.4)** | `corpus` and `diagnostics` are currently separate nav tabs in `Home.tsx:84-94`. | Merging must preserve document ingestion controls, Celery task monitor, and health telemetry. | Merge into unified top-bar `System Diagnostics` tab with sub-panels: Telemetry, Literature Management, and Data Quality Metrics. |
| **7** | **Hide-Nulls Rule (P9)** | UI displays empty fields or "Unverified — no UniProt match" placeholders. | Incomplete external databases clutter the interface with N/A. | Strict `hide-nulls` policy: fields with `not_checked` or `checked_not_found` are completely hidden from UI display. |
| **8** | **Client-Side Fallback Engine** | `frontend/client/src/lib/bio_client_engine.ts` duplicates logic with hardcoded mutations and mock regexes. | Risk of frontend displaying stale or fabricated fallback data if backend is unreachable. | Remove hardcoded mutation mock dictionaries, ensuring frontend displays only authenticated backend data or explicit offline warnings. |

---

## 2. Risk Mitigation Plan

1. **Volume Management for Microbial Taxa**:
   - *Mammuthus*, *Coelodonta*, *Smilodon*, etc., have manageable proteomes (< 150 entries each).
   - For *Yersinia pestis* and *Influenza A virus*, we store the canonical ancient loci (Pla, Caf1, YopM, HA, NA, PB2) and filter bulk strains using the agreed relevance rules (§P3.5).
2. **Provenance & Auditability**:
   - Every stored record must retain `source_db`, `source_record_id`, `retrieved_at`, `query_used`, and `raw_response_ref`.
   - All legacy data remains immutably archived in `archive/legacy_20261013/`.
