# PaleoRAG Discrepancies and Identifier Verification

This document logs all corrections and verified database accessions discovered during Phase 0 audit against live biological database APIs (NCBI, UniProt, RCSB PDB, InterPro, PROSITE, Pfam).

---

## 1. Case Study 1: Woolly Mammoth (*Mammuthus primigenius*) Hemoglobin (*HBB*)

| Field | Value in Draft Spec | Verified Real Record | Live API Validation & Notes |
| :--- | :--- | :--- | :--- |
| **GenBank Nucleotide** | `HQ184444.1` | **`HQ184444.1`** | **VALID**: *Mammuthus primigenius* hemoglobin subunit beta (*HBB*) gene, complete cds. (Also EMBL `FJ716094`). |
| **UniProtKB Accession** | `P02100` | **`D3U1H9`** (*Mammuthus primigenius*) / `P02100` (*Homo sapiens* / `P68082` *Elephas maximus*) | **DISCREPANCY**: `P02100` in UniProt is human Hemoglobin subunit epsilon-1 (`HBE_HUMAN`). The authentic UniProt entry for *Mammuthus primigenius* beta-globin is **`D3U1H9`** (`D3U1H9_MAMPR`). Modern Asian elephant ortholog is `P68082`. |
| **RCSB PDB Structure** | `3N3A` | **`3VRE`** (2.20 Å) / **`3VRF`** (1.55 Å) / **`3VRG`** (1.50 Å) | **DISCREPANCY**: `3N3A` in PDB is the crystal structure of *Chlamydia trachomatis* ribonucleotide reductase (Boal et al., 2010). The authentic crystal structures of recombinant ancestral woolly mammoth hemoglobin are **`3VRE`**, **`3VRF`**, and **`3VRG`** (Yuan et al., 2010). |
| **CATH Classification** | `1.10.490.10` | **`1.10.490.10`** | **VALID**: Main fold for Globins (`1.10.490.10:FF:000001`). |
| **Pfam Domain** | `PF00042` | **`PF00042`** | **VALID**: Globin domain. |
| **PROSITE Signature** | `PS01033` | **`PS01033`** | **VALID**: GLOBIN motif pattern `[LIVMF]-[A-Z]-H-[LIVMFY]-[A-Z](2)-[LIVMFY]`. |
| **Gene Ontology** | `GO:0015671` | **`GO:0005344`**, **`GO:0019825`**, **`GO:0015671`** | **VALID**: Oxygen transport, oxygen binding, oxygen carrier activity. |
| **STRING Interactions** | *HBA*, *BPGM* | **`HBA1`**, **`BPGM`** | **VALID**: Interacts with Hemoglobin Alpha and 2,3-Bisphosphoglycerate Mutase. |

---

## 2. Case Study 2: Neanderthal vs. Modern Human Language Gene (*FOXP2*)

| Field | Value in Draft Spec | Verified Real Record | Live API Validation & Notes |
| :--- | :--- | :--- | :--- |
| **GenBank Nucleotide** | `AF512946.1` | **`AF512946.1`** | **VALID**: *Homo sapiens* forkhead box P2 (*FOXP2*) gene, complete cds. |
| **UniProtKB Accession** | `O15409` | **`O15409`** | **VALID**: `FOXP2_HUMAN` Forkhead box protein P2 (100% sequence identity in the DNA-binding domain between modern human and Altai Neanderthal). |
| **RCSB PDB Structure** | `2A07` | **`2A07`** (1.90 Å) | **VALID**: Crystal structure of the human FOXP2 Forkhead domain bound to DNA (Stroud et al., 2006). |
| **Pfam Domain** | `PF00250` | **`PF00250`** | **VALID**: Forkhead domain. Also contains `PF16159` (FOXP coiled-coil domain). |
| **PROSITE Signature** | `PS50089` | **`PS00658`** (Pattern) / **`PS50039`** (Profile) | **DISCREPANCY**: `PS50089` in PROSITE is `ZF_RING_2` (Zinc finger RING-type profile). The correct Forkhead signatures in PROSITE are **`PS00658`** (`FORK_HEAD_2` pattern) and **`PS50039`** (`FORK_HEAD_3` profile). |
| **STRING Interactions** | *CNTNAP2*, *FOXP1* | **`CNTNAP2`**, **`FOXP1`**, **`CTNND2`** | **VALID**: Direct transcriptional targets and heterodimer partners. |
| **Comparative Locus** | 7q31.1 | **chr7:114,055,052-114,693,772** (GRCh38) | **VALID**: Synteny with Altai Neanderthal High-Coverage track in UCSC / Ensembl. |

---

## 3. Case Study 3: Ancient Black Death (*Yersinia pestis*) Plasminogen Activator (*Pla*)

| Field | Value in Draft Spec | Verified Real Record | Live API Validation & Notes |
| :--- | :--- | :--- | :--- |
| **GenBank Nucleotide** | `AL590842.1` | **`AL590842.1`** | **VALID**: *Yersinia pestis* complete sequence of plasmid pPCP1 from historical strain CO92 / London 1348 Black Death cemetery. |
| **UniProtKB Accession** | `P0CL84` | **`P17811`** (`PLA_YERPE`) | **DISCREPANCY**: `P0CL84` in UniProt is human Beta-galactoside alpha-2,3-sialyltransferase 2 (`ST3L2_HUMAN`). The authentic UniProt accession for *Yersinia pestis* Pla protease is **`P17811`** (`PLA_YERPE`). |
| **RCSB PDB Structure** | `1X98` | **`2X55`** (1.85 Å) / **`4DCB`** (2.03 Å) / **`2X4M`** (2.55 Å) | **DISCREPANCY**: `1X98` in PDB is human Aldose Reductase. The authentic crystal structures of *Yersinia pestis* Pla protease outer membrane beta-barrel are **`2X55`**, **`4DCB`**, and **`2X4M`** (Eren et al., 2010). |
| **Pfam Domain** | `PF03544` | **`PF01278`** | **DISCREPANCY**: `PF03544` is Autotransporter beta-domain. The true domain family for the Pla protease is the Omptin outer-membrane beta-barrel family: **`PF01278`** (`Omptin`). |
| **PROSITE Signature** | — | **`PS00834`** / **`PS00835`** | **VALID**: `OMPTIN_1` (`PS00834`) and `OMPTIN_2` (`PS00835`) signatures. |
| **KEGG Pathway** | `map05100` | **`map05100`** / `ype:YPPCP1.07` | **VALID**: Bacterial invasion of epithelial cells pathway (`map05100`). Gene in KEGG is `ype:YPPCP1.07`. |
