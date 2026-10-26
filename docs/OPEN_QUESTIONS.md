# OPEN_QUESTIONS.md — Human Decisions & Open Questions Log

This document tracks all required decisions, architectural questions, and blocking gates in accordance with Prime Directive 1 and Section 1 of `PALEORAG_PATCH_PLAN.md`.

---

## 1. Human Decisions Required (from Section 1)

### H1: Taxa List Scope & Authoritative Source
- **Status**: RESOLVED BY HUMAN (2026-10-13)
- **Decision**: Keep the current 18 codified taxa from `backend/data/paleo_atlas_registry.json` as the authoritative scope.
- **Repository Finding**: Confirmed the 18 taxa covering Late Pleistocene megafauna, archaic hominins, and historical pathogens.
- **Action**: Phase P2 will resolve and round-trip verify NCBI Taxonomy IDs and PBDB IDs across exactly these 18 taxa.

---

### H2: Taxon Scope in UniProt (Exact vs Descendants)
- **Status**: RESOLVED BY HUMAN (2026-10-13)
- **Decision**: Pull all queries matching to each taxon and format as a list. Include descendant subspecies/strains where taxonomically relevant (especially for historical strains of microbes).

---

### H3: UniProt Scope (Swiss-Prot Reviewed vs TrEMBL Unreviewed)
- **Status**: RESOLVED BY HUMAN (2026-10-13)
- **Decision**: Both Swiss-Prot (reviewed) and TrEMBL (unreviewed) entries are approved. Every stored record must clearly indicate from which database it was retrieved (`reviewed: bool` / source field).
- **Measured Probe Counts**: 23 reviewed + 387 unreviewed = 410 total entries across the 16 extinct animal/hominin taxa; full counts logged in `docs/verification/p3_count_probe_measured.json`.


---

### H4: Definition of "Relevant" for Unmapped Proteins
- **Status**: PENDING HUMAN CONFIRMATION (Needed by Phase P3)
- **Question**: Adopt proposed rules R1–R4 in §P3.5 to keep proteins without PDB structures?
  - R1: Reviewed (Swiss-Prot) entry.
  - R2: Has >= 1 literature citation passing Phase P6 rules.
  - R3: Listed in project gene/protein panel found in repo.
  - R4: Has authoritative ortholog link to a protein satisfying R1–R3.
- **Recommendation**: Confirm rules R1–R4. Unmapped proteins failing all four are moved to `rejected` with `NOT_RELEVANT`.

---

### H5: Extant Relative Comparison Taxon per Extinct Taxon
- **Status**: RESOLVED BY HUMAN (2026-10-13)
- **Decision**: Confirmed the 18 paired living sister species from the repository:
  - *Mammuthus primigenius* $\rightarrow$ *Elephas maximus* (Asian Elephant)
  - *Homo neanderthalensis* $\rightarrow$ *Homo sapiens* (Modern Human)
  - *Yersinia pestis* $\rightarrow$ *Yersinia pseudotuberculosis* (or modern *Y. pestis*)
  - *Aenocyon dirus* $\rightarrow$ *Canis lupus* (Gray Wolf)
  - *Panthera spelaea* $\rightarrow$ *Panthera leo* (Modern Lion)
  - *Bison priscus* $\rightarrow$ *Bison bison* (American Bison)
  - *Homo sapiens denisova* $\rightarrow$ *Homo sapiens* (Modern Human)
  - *Thylacinus cynocephalus* $\rightarrow$ *Sarcophilus harrisii* (Tasmanian Devil)
  - *Coelodonta antiquitatis* $\rightarrow$ *Ceratotherium simum* (White Rhinoceros)
  - *Smilodon fatalis* $\rightarrow$ *Felis catus* / *Panthera tigris* (Modern Felid)
  - *Raphus cucullatus* $\rightarrow$ *Caloenas nicobarica* (Nicobar Pigeon)
  - *Ectopistes migratorius* $\rightarrow$ *Patagioenas fasciata* (Band-tailed Pigeon)
  - *Mylodon darwinii* $\rightarrow$ *Choloepus hoffmanni* (Two-toed Sloth)
  - *Arctodus simus* $\rightarrow$ *Tremarctos ornatus* (Spectacled Bear)
  - *Influenza A virus (H1N1 1918)* $\rightarrow$ *Influenza A virus (modern seasonal)*
  - *Doedicurus clavicaudatus* $\rightarrow$ *Priodontes maximus* / *Dasypus novemcinctus* (Armadillo)
  - *Toxodon platensis* $\rightarrow$ *Ceratotherium simum* / *Equus caballus*
  - *Dinornis robustus* $\rightarrow$ *Apteryx mantelli* (North Island Brown Kiwi)
- **Action**: Phase P8 will query Ensembl Compara, OrthoDB, along with UniProt and NCBI resources to retrieve orthology mappings and chromosomal coordinates.

---

### H6: RDBMS Decision Gate
- **Status**: BLOCKING AT END OF PHASE P1
- **Question**: Maintain schema-validated local files (Option A) vs Embedded SQLite (Option B) vs Client/Server RDBMS (Option C)?
- **Deliverable**: `docs/RDBMS_DECISION.md` will present empirical volume and query benchmarks for human sign-off.

---

### H7: AlphaFold & Predicted Structures Display
- **Status**: PENDING (Needed by Phase P5)
- **Question**: Show AlphaFold predicted structures as supplementary with clear "predicted" labeling?
- **Recommendation**: Yes; PDB field remains `null` when no experimental structure exists.

---

### H8: Literature Full-Text vs Abstract-Only Licensing
- **Status**: RESOLVED BY HUMAN (2026-10-13)
- **Decision**: Ingest abstracts for all papers, plus full-text XML/text for open-access papers (PMC Open Access subset / CC-BY / CC0 / bioRxiv) with license tag recorded on each paper record.
- **Action**: Phase P6 will fetch PubMed/PMC abstracts and open-access full texts, recording license status and rejecting/flagging non-conforming items.

---

### H9: LLM & Embedding Providers for RAG
- **Status**: RESOLVED BY HUMAN (2026-10-13)
- **Decision**: Reuse existing local-first stack: PubMedBERT dense embeddings (`NeuML/pubmedbert-base-embeddings`) + local Ollama (`llama3.2:1b`) with zero remote egress.
- **Action**: Phase P7 will pin embedding model and revision, cache embeddings locally by SHA-256 hash, and ground generation strictly on retrieved chunks.

---

### H10: KEGG Usage Terms
- **Status**: RESOLVED BY HUMAN (2026-10-13)
- **Decision**: Academic REST lookup and canonical URL linking (`https://www.kegg.jp/entry/{identifier}`) approved under fair-use terms.
- **Action**: Implemented in Phase P5.
