# LITERATURE_SEARCH.md — Literature Search & Evidence Linking Protocol

This document defines the query templates, boolean logic, evidence tier taxonomy, and validation rules for Phase P6 per §P6 of `PALEORAG_PATCH_PLAN.md`.

---

## 1. Evidence Tier Taxonomy

Every paper linked to a protein record carries an explicit `evidence_type`:

| Evidence Tier | Code | Source / Trigger | Precision Profile | Validation Required? |
|---|---|---|---|---|
| **Tier A** | `uniprot_citation` | Citations explicitly listed in the protein's UniProtKB record (`references[].citation`). | Ultra-high (manually curated or author-deposited). | Verified PMID/DOI fetch; no text co-occurrence filtering needed. |
| **Tier A** | `pdb_primary_citation` | Primary publication listed for the mapped PDB structure (`rcsb_primary_citation`). | Ultra-high (structural deposition paper). | Verified PMID/DOI fetch; no text co-occurrence filtering needed. |
| **Tier A** | `xref_link` | Citations directly linked to cross-referenced records (e.g. NCBI Gene PMID cross-references). | High (curated cross-reference). | Verified PMID/DOI fetch. |
| **Tier B** | `keyword_search_validated` | Literature search hits from PubMed and Europe PMC REST APIs using structured boolean queries. | Medium-High (automated query hit). | **Mandatory code validation**: matched taxon name/synonym AND matched gene/protein cue with offsets. |

---

## 2. Query Construction Specifications (Tier B)

Queries are executed against PubMed (E-utilities `esearch`) and Europe PMC REST API (`/search`).

### 2.1 Standard Query Template
For a given extinct protein with organism taxon name $T$, taxon synonyms $T_{syn}$, gene symbol $G$, gene synonyms $G_{syn}$, protein name $P$, and UniProt accession $A$:

```text
("{T}"[Title/Abstract] OR "{T_syn_1}"[Title/Abstract]) 
AND 
("{P}"[Title/Abstract] OR "{G}"[Title/Abstract] OR "{A}"[All Fields])
```

### 2.2 Short Gene Symbol Rule (Disambiguation)
- **Constraint**: If gene symbol $G$ has length $\le 4$ characters (e.g., `D`, `HBA`, `HA`, `NP`), $G$ alone is **forbidden** as a solitary query token because short symbols create thousands of spurious homonym hits.
- **Rule**: Short gene symbols must co-occur with either:
  1. The full protein name (e.g., `"hemoglobin alpha"` OR `"hemoglobin"`), OR
  2. The specific taxon scientific name or vernacular name in the same sentence or title/abstract field.
- If a hit only contains the short gene symbol without the required co-occurring cue, it is categorized as `rejected` with reason code `NOT_RELEVANT`.

### 2.3 Field Tagging & Syntax
- **PubMed**:
  - Organism terms: `[Title/Abstract]`
  - Protein/Gene names: `[Title/Abstract]`
  - Accessions / PDB IDs: `[All Fields]`
- **Europe PMC**:
  - `(TITLE:"{T}" OR ABSTRACT:"{T}") AND (TITLE:"{P}" OR ABSTRACT:"{P}" OR "{A}")`

---

## 3. Tier B Acceptance & Validation Rules (§P6.2)

Every candidate paper retrieved via Tier B must pass automated text verification against its retrieved Title and Abstract:

1. **Taxon Cue Check**:
   - The text must contain a recognized scientific name (e.g., *Mammuthus primigenius*), genus (e.g., *Mammuthus*), or accepted common name/synonym (e.g., *woolly mammoth*) using word boundary regex (`\b...\b`, case-insensitive).
2. **Protein Cue Check**:
   - The text must contain the UniProt accession, mapped PDB ID, recommended protein name, alternative protein name, or gene symbol.
3. **Offset Evidence Recording**:
   - Every accepted link records `matched_strings_json`:
     ```json
     {
       "taxon_matches": [{"term": "Mammuthus primigenius", "start": 42, "end": 64, "field": "title"}],
       "protein_matches": [{"term": "hemoglobin", "start": 85, "end": 95, "field": "abstract"}]
     }
     ```
4. **Classification Protocol**:
   - **Accepted**: Both Taxon cue AND Protein cue present and validated.
   - **Rejected (`NOT_RELEVANT`)**: Hit missing either Taxon cue or Protein cue.
   - **Pending Human Review (`PENDING_HUMAN_REVIEW`)**: Hit contains ambiguous match (e.g., partial protein stem) or conflicting taxonomic context.

---

## 4. Integrity & Licensing Rules (§P6.3 & H8)

1. **Authoritative Retrieval Only**: Every paper must be fetched from NCBI E-utilities or Europe PMC REST API. Title, journal, year, and abstract are stored **as retrieved**.
2. **Deduplication**: Deduplicated across sources by unique primary key: `pmid` (preferred) or canonical lowercase `doi`.
3. **Retraction Detection**:
   - Source metadata is inspected for publication types: `Retracted Publication`, `retraction-notice`, or Europe PMC `isRetracted == "Y"`.
   - Stored in `papers.is_retracted = 1` with `retraction_details`. Retracted papers are visibly flagged.
4. **Licensing Compliance (Decision H8)**:
   - All retrieved papers store title and abstract.
   - Papers in PMC Open Access subset or bioRxiv preprints with approved licenses (`CC-BY`, `CC0`, `CC-BY-NC`) store full text paths and `license` tags.
   - Non-OA publications are stored as abstract-only with `license = "Abstract only / All rights reserved"`.
