"""
Unified biological data aggregator: orchestrates multi-database cross-referencing
across NCBI, UniProt, RCSB PDB, Pfam, PROSITE, KEGG, STRING, and Ensembl.
"""
from __future__ import annotations

import logging
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
    },
    "HBB": {
        "gene": "HBB",
        "organism": "Mammuthus primigenius",
        "nucleotide_acc": "HQ184444.1",
        "uniprot_acc": "D3U1H9",
        "pdb_id": "3VRF",
        "kegg_pathway": "map05100",
        "locus": "HBB",
    },
    "FOXP2": {
        "gene": "FOXP2",
        "organism": "Homo sapiens / Homo neanderthalensis",
        "nucleotide_acc": "AF512946.1",
        "uniprot_acc": "O15409",
        "pdb_id": "2A07",
        "kegg_pathway": "map05100",
        "locus": "FOXP2",
    },
    "PLA": {
        "gene": "pla",
        "organism": "Yersinia pestis",
        "nucleotide_acc": "AL590842.1",
        "uniprot_acc": "P17811",
        "pdb_id": "2X55",
        "kegg_pathway": "map05100",
        "locus": "pla",
    },
    "YERSINIA": {
        "gene": "pla",
        "organism": "Yersinia pestis",
        "nucleotide_acc": "AL590842.1",
        "uniprot_acc": "P17811",
        "pdb_id": "2X55",
        "kegg_pathway": "map05100",
        "locus": "pla",
    },
}


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

    def lookup(self, query: str) -> BioLookupResponse:
        clean_q = query.strip().upper()
        mapping = None

        # Check known paleogenomic targets
        for key, target in PREINDEXED_ENTITIES.items():
            if key in clean_q:
                mapping = target
                break

        organism = mapping.get("organism") if mapping else None
        nuc_rec = None
        prot_rec = None
        struct_rec = None
        domains: list[DomainHit] = []
        pathways = []
        interactions = []
        locus = None

        # 1. Fetch Protein Record
        uniprot_id = mapping.get("uniprot_acc") if mapping else None
        if not uniprot_id and clean_q.startswith(("P", "Q", "O", "D")):
            uniprot_id = clean_q

        if uniprot_id:
            try:
                prot_rec = self.uniprot.get_protein(uniprot_id)
                if not organism:
                    organism = prot_rec.organism
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
            interactions = self.func.get_string_interactions(gene_symbol, limit=8)
            kegg_hit = self.func.get_kegg_pathway(mapping.get("kegg_pathway", "map05100") if mapping else "map05100")
            if kegg_hit:
                pathways.append(kegg_hit)
            locus = self.genomics.get_gene_locus(gene_symbol)

        return BioLookupResponse(
            query=query,
            organism=organism,
            nucleotide_record=nuc_rec,
            protein_record=prot_rec,
            structure_record=struct_rec,
            domains=domains,
            pathways=pathways,
            interactions=interactions,
            locus=locus,
        )
