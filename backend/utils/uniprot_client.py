"""
UniProtKB REST API client: Swiss-Prot & TrEMBL parser, features extractor
(active sites, disulfide bonds, PTMs), and PIR cross-reference resolver.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from backend.api.bio_schemas import ProteinRecord
from backend.config import Settings, get_settings
from backend.utils.error_types import DatabaseClientError, DatabaseNotFoundError
from backend.utils.http_client import BioHttpClient, get_bio_http_client

logger = logging.getLogger(__name__)


class UniProtClient:
    """Client for UniProtKB REST API (Swiss-Prot / TrEMBL)."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        http_client: Optional[BioHttpClient] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.http = http_client or get_bio_http_client()
        self.base_url = self.settings.uniprot_api_base.rstrip("/")

    def get_protein(self, accession: str) -> ProteinRecord:
        """Fetch protein entry by UniProtKB accession and normalize."""
        clean_acc = accession.strip().upper()
        url = f"{self.base_url}/uniprotkb/{clean_acc}.json"

        try:
            data = self.http.get_json(url)
        except DatabaseNotFoundError:
            raise DatabaseNotFoundError(f"UniProt entry '{clean_acc}' not found.", database="uniprot")

        return self._normalize_entry(data)

    def search_proteins(self, query: str, limit: int = 5) -> list[ProteinRecord]:
        """Search UniProtKB by free text, gene name, or taxon query."""
        url = f"{self.base_url}/uniprotkb/search"
        data = self.http.get_json(
            url,
            params={
                "query": query,
                "size": limit,
                "format": "json",
            },
        )
        results = data.get("results", [])
        return [self._normalize_entry(entry) for entry in results]

    def _normalize_entry(self, data: dict[str, Any]) -> ProteinRecord:
        accession = data.get("primaryAccession", "")
        entry_name = data.get("uniProtkbId", accession)

        # Protein recommended name
        protein_desc = data.get("proteinDescription", {})
        rec_name = (
            protein_desc.get("recommendedName", {}).get("fullName", {}).get("value")
            or (protein_desc.get("submissionNames", [{}])[0].get("fullName", {}).get("value") if protein_desc.get("submissionNames") else "")
            or entry_name
        )

        # Organism
        org_data = data.get("organism", {})
        organism_name = org_data.get("scientificName", "Unknown organism")
        organism_id = org_data.get("taxonId")

        # Sequence
        seq_data = data.get("sequence", {})
        sequence = seq_data.get("value", "")
        length = seq_data.get("length", len(sequence))

        # Features (active sites, disulfide bonds, PTMs)
        active_sites = []
        disulfide_bonds = []
        ptms = []

        for feat in data.get("features", []):
            ftype = feat.get("type", "")
            loc = feat.get("location", {})
            start = loc.get("start", {}).get("value")
            end = loc.get("end", {}).get("value")
            desc = feat.get("description", "")

            feat_item = {
                "type": ftype,
                "start": start,
                "end": end,
                "description": desc,
            }

            if ftype in ("Active site", "Binding site", "Site"):
                active_sites.append(feat_item)
            elif ftype == "Disulfide bond":
                disulfide_bonds.append(feat_item)
            elif ftype in ("Modified residue", "Glycosylation", "Lipidation", "Cross-link"):
                ptms.append(feat_item)

        # Cross references (PIR, PDB, Pfam, PROSITE, GO, KEGG, Ensembl)
        pir_ids: list[str] = []
        cross_refs: dict[str, list[dict[str, Any]]] = {}

        for xref in data.get("uniProtKBCrossReferences", []):
            db = xref.get("database", "")
            xid = xref.get("id", "")
            props = {p.get("key", ""): p.get("value", "") for p in xref.get("properties", [])}
            entry = {"id": xid, "properties": props}

            if db == "PIR":
                pir_ids.append(xid)

            if db not in cross_refs:
                cross_refs[db] = []
            cross_refs[db].append(entry)

        return ProteinRecord(
            accession=accession,
            entry_name=entry_name,
            protein_name=rec_name,
            organism=organism_name,
            organism_id=organism_id,
            sequence=sequence,
            length=length,
            active_sites=active_sites,
            disulfide_bonds=disulfide_bonds,
            ptms=ptms,
            pir_ids=pir_ids,
            cross_references=cross_refs,
        )
