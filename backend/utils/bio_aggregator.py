"""
Unified biological data aggregator: orchestrates multi-database cross-referencing
across NCBI, UniProt, RCSB PDB, Pfam, PROSITE, KEGG, STRING, and Ensembl.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from backend.api.bio_schemas import BioLookupResponse, DomainHit
from backend.config import Settings, get_settings
from backend.utils.functional_client import FunctionalClient
from backend.utils.genomics_client import GenomicsClient
from backend.utils.http_client import BioHttpClient, get_bio_http_client
from backend.utils.ncbi_client import NCBIClient
from backend.utils.pdb_client import PDBClient
from backend.utils.uniprot_client import UniProtClient

logger = logging.getLogger(__name__)

# Pre-indexed mappings for primary paleogenomic case studies
PREINDEXED_ENTITIES = {
    "MAMMOTH": {
        "gene": "HBB",
        "organism": "Mammuthus primigenius",
        "nucleotide_acc": "HQ184444.1",
        "uniprot_acc": "D3U1H9",
        "pdb_id": "3VRF",
        "kegg_pathway": "map05100",
        "locus": "HBB",
        "cache_key": "HBB",
    },
    "HBB": {
        "gene": "HBB",
        "organism": "Mammuthus primigenius",
        "nucleotide_acc": "HQ184444.1",
        "uniprot_acc": "D3U1H9",
        "pdb_id": "3VRF",
        "kegg_pathway": "map05100",
        "locus": "HBB",
        "cache_key": "HBB",
    },
    "FOXP2": {
        "gene": "FOXP2",
        "organism": "Homo sapiens / Homo neanderthalensis",
        "nucleotide_acc": "AF512946.1",
        "uniprot_acc": "O15409",
        "pdb_id": "2A07",
        "kegg_pathway": "map05100",
        "locus": "FOXP2",
        "cache_key": "FOXP2",
    },
    "PLA": {
        "gene": "pla",
        "organism": "Yersinia pestis",
        "nucleotide_acc": "AL590842.1",
        "uniprot_acc": "P17811",
        "pdb_id": "2X55",
        "kegg_pathway": "map05100",
        "locus": "pla",
        "cache_key": "Pla",
    },
    "YERSINIA": {
        "gene": "pla",
        "organism": "Yersinia pestis",
        "nucleotide_acc": "AL590842.1",
        "uniprot_acc": "P17811",
        "pdb_id": "2X55",
        "kegg_pathway": "map05100",
        "locus": "pla",
        "cache_key": "Pla",
    },
}

_PREINDEXED_CACHE: dict[str, dict] = {}


def _get_preindexed_cache() -> dict[str, dict]:
    global _PREINDEXED_CACHE
    if not _PREINDEXED_CACHE:
        possible_paths = [
            Path(__file__).parent.parent / "data" / "preindexed_case_studies.json",
            Path(__file__).parent.parent.parent / "frontend" / "client" / "src" / "lib" / "preindexed_case_studies.json",
        ]
        for p in possible_paths:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        _PREINDEXED_CACHE = json.load(f)
                    break
                except Exception as exc:
                    logger.debug(f"Failed to load preindexed cache from {p}: {exc}")
    return _PREINDEXED_CACHE


class BioAggregator:
    """Aggregates multi-database biological knowledge for an entity or query."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        http_client: Optional[BioHttpClient] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.http = http_client or get_bio_http_client()
        self.ncbi = NCBIClient(settings=self.settings, http_client=self.http)
        self.uniprot = UniProtClient(settings=self.settings, http_client=self.http)
        self.pdb = PDBClient(settings=self.settings, http_client=self.http)
        self.func = FunctionalClient(settings=self.settings, http_client=self.http)
        self.genomics = GenomicsClient(settings=self.settings, http_client=self.http)

    def lookup(self, query: str, organism: Optional[str] = None) -> BioLookupResponse:
        clean_q = query.strip().upper()
        mapping = None

        # Check known paleogenomic targets
        for key, target in PREINDEXED_ENTITIES.items():
            if key in clean_q or clean_q in key:
                mapping = target
                break

        # Fast pre-cached path for all Atlas entries and case studies
        cache_data = _get_preindexed_cache()

        def _finalize_cached_resp(hit: dict) -> BioLookupResponse:
            r = BioLookupResponse(**hit)
            r.query = query
            if organism:
                r.organism = organism
            if r.protein_record and r.protein_record.sequence and not any(d.id.startswith("PS") for d in r.domains):
                try:
                    scanned = self.func.scan_prosite_motifs(r.protein_record.sequence)
                    r.domains.extend(scanned)
                except Exception:
                    pass
            return r

        if clean_q in cache_data:
            return _finalize_cached_resp(cache_data[clean_q])

        for k, hit in cache_data.items():
            if len(k) >= 3 and (k == clean_q or k in clean_q or clean_q in k):
                return _finalize_cached_resp(hit)

        if mapping and mapping.get("cache_key") and mapping["cache_key"] in cache_data:
            return _finalize_cached_resp(cache_data[mapping["cache_key"]])

        target_organism = organism or (mapping.get("organism") if mapping else None)
        nuc_rec = None
        prot_rec = None
        struct_rec = None
        domains: list[DomainHit] = []
        pathways = []
        interactions = []
        locus = None

        # Check if query is Pfam accession
        if clean_q.startswith("PF") and len(clean_q) in (7, 8):
            try:
                pfam_hit = self.func.get_pfam_domain(clean_q)
                if pfam_hit:
                    domains.append(pfam_hit)
            except Exception as exc:
                logger.debug(f"Pfam query failed for {clean_q}: {exc}")

        # 1. Fetch Protein Record
        uniprot_id = mapping.get("uniprot_acc") if mapping else None
        if not uniprot_id and clean_q.startswith(("P", "Q", "O", "D")) and len(clean_q) in (6, 10):
            uniprot_id = clean_q

        if uniprot_id:
            try:
                prot_rec = self.uniprot.get_protein(uniprot_id)
                if not target_organism:
                    target_organism = prot_rec.organism
                # Scan PROSITE motifs on protein sequence
                if prot_rec.sequence:
                    domains.extend(self.func.scan_prosite_motifs(prot_rec.sequence))
            except Exception as exc:
                logger.debug(f"Protein lookup failed for {uniprot_id}: {exc}")

        # 2. Fetch Nucleotide Record
        nuc_acc = mapping.get("nucleotide_acc") if mapping else None
        if not nuc_acc and (clean_q.startswith(("NC_", "HQ", "AF", "AL", "NM_")) or "." in clean_q):
            nuc_acc = clean_q

        if nuc_acc:
            try:
                nuc_rec = self.ncbi.get_sequence_record(nuc_acc)
            except Exception as exc:
                logger.debug(f"Nucleotide lookup failed for {nuc_acc}: {exc}")

        # 3. Fetch PDB Structure
        pdb_id = mapping.get("pdb_id") if mapping else None
        if not pdb_id and len(clean_q) == 4 and (clean_q[0].isdigit() or clean_q in ("2A07", "3VRF", "2X55")):
            pdb_id = clean_q

        if pdb_id:
            try:
                struct_rec = self.pdb.get_structure(pdb_id)
            except Exception as exc:
                logger.debug(f"PDB lookup failed for {pdb_id}: {exc}")

        # 4. Fetch Pathways & Interactions
        gene_symbol = mapping.get("gene") if mapping else clean_q
        if gene_symbol:
            try:
                interactions = self.func.get_string_interactions(gene_symbol, limit=8)
            except Exception as exc:
                logger.debug(f"STRING interaction lookup failed: {exc}")

            try:
                kegg_id = mapping.get("kegg_pathway", "map05100") if mapping else "map05100"
                kegg_hit = self.func.get_kegg_pathway(kegg_id)
                if kegg_hit:
                    pathways.append(kegg_hit)
            except Exception as exc:
                logger.debug(f"KEGG pathway lookup failed: {exc}")

            try:
                # Avoid querying human Ensembl for non-mammalian/bacterial genes
                org_lower = (target_organism or "").lower()
                if not org_lower or any(k in org_lower for k in ("homo", "human", "neanderthal", "mammuthus", "mammoth")):
                    locus = self.genomics.get_gene_locus(gene_symbol)
            except Exception as exc:
                logger.debug(f"Genomics locus lookup failed: {exc}")

        return BioLookupResponse(
            query=query,
            organism=target_organism,
            nucleotide_record=nuc_rec,
            protein_record=prot_rec,
            structure_record=struct_rec,
            domains=domains,
            pathways=pathways,
            interactions=interactions,
            locus=locus,
        )
