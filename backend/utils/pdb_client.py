"""
RCSB PDB & CATH/SCOP client: macromolecular 3D structure metadata, coordinate retrieval,
structural fold classification, and ancestral mutation residue mapping.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from backend.api.bio_schemas import StructureRecord
from backend.config import Settings, get_settings
from backend.utils.error_types import DatabaseNotFoundError
from backend.utils.http_client import BioHttpClient, get_bio_http_client

logger = logging.getLogger(__name__)


class PDBClient:
    """Client for RCSB PDB, PDBe SIFTS (CATH & SCOP), and mutation mapping."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        http_client: Optional[BioHttpClient] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.http = http_client or get_bio_http_client()
        self.rcsb_base = self.settings.rcsb_api_base.rstrip("/")
        self.pdbe_base = "https://www.ebi.ac.uk/pdbe/api/mappings"

    def get_structure(self, pdb_id: str) -> StructureRecord:
        """Fetch structure metadata, CATH, and SCOP classifications for a PDB ID."""
        clean_id = pdb_id.strip().upper()
        url = f"{self.rcsb_base}/core/entry/{clean_id}"

        try:
            data = self.http.get_json(url)
        except DatabaseNotFoundError:
            raise DatabaseNotFoundError(f"PDB structure '{clean_id}' not found.", database="rcsb_pdb")

        struct_title = data.get("struct", {}).get("title", "")
        entry_info = data.get("rcsb_entry_info", {})
        resolution = entry_info.get("resolution_combined", [None])[0]
        exptl = data.get("exptl", [{}])
        method = exptl[0].get("method", "Unknown")
        deposit_date = data.get("rcsb_accession_info", {}).get("deposit_date", "")

        # Polymer chains
        polymer_entity_ids = entry_info.get("polymer_entity_count_protein", 1)
        chains: list[str] = []
        try:
            entity_data = self.http.get_json(f"{self.rcsb_base}/core/polymer_entity/{clean_id}/1")
            for instance in entity_data.get("rcsb_polymer_entity_container_identifiers", {}).get("auth_asym_ids", []):
                chains.append(instance)
        except Exception:
            chains = ["A"]

        # Ligands
        ligands: list[str] = entry_info.get("nonpolymer_bound_components", [])

        # Fetch CATH & SCOP mappings via PDBe
        cath_codes, cath_names = self._fetch_cath_classification(clean_id)
        scop_folds = self._fetch_scop_classification(clean_id)

        coordinates_url = f"https://files.rcsb.org/download/{clean_id}.cif"

        return StructureRecord(
            pdb_id=clean_id,
            title=struct_title,
            resolution_angstrom=resolution,
            method=method,
            deposit_date=deposit_date,
            cath_codes=cath_codes,
            cath_names=cath_names,
            scop_folds=scop_folds,
            ligands=ligands,
            chains=chains,
            coordinates_url=coordinates_url,
        )

    def fetch_coordinates_pdb(self, pdb_id: str) -> str:
        """Download raw atomic coordinates in PDB format."""
        clean_id = pdb_id.strip().upper()
        url = f"https://files.rcsb.org/download/{clean_id}.pdb"
        return self.http.get_text(url)

    def _fetch_cath_classification(self, pdb_id: str) -> tuple[list[str], list[str]]:
        """Query PDBe SIFTS for CATH structural domains."""
        url = f"{self.pdbe_base}/cath/{pdb_id.lower()}"
        codes: list[str] = []
        names: list[str] = []
        try:
            data = self.http.get_json(url)
            cath_dict = data.get(pdb_id.lower(), {}).get("CATH", {})
            for cath_id, details in cath_dict.items():
                codes.append(cath_id)
                names.append(details.get("homology", cath_id))
        except Exception:
            pass
        return codes, names

    def _fetch_scop_classification(self, pdb_id: str) -> list[str]:
        """Query PDBe SIFTS for SCOP fold classifications."""
        url = f"{self.pdbe_base}/scop/{pdb_id.lower()}"
        folds: list[str] = []
        try:
            data = self.http.get_json(url)
            scop_dict = data.get(pdb_id.lower(), {}).get("SCOP", {})
            for scop_id, details in scop_dict.items():
                fold_desc = details.get("fold", details.get("family", scop_id))
                folds.append(fold_desc)
        except Exception:
            pass
        return folds

    def map_mutations_to_structure(
        self,
        pdb_id: str,
        mutations: list[dict[str, Any]],
        chain: str = "A",
    ) -> list[dict[str, Any]]:
        """
        Map substitutions (e.g. ancestral mammoth vs extant Asian elephant)
        to PDB residue numbering for highlighting in 3D molecular viewer.
        mutations format: [{"ancestral": "T", "position": 12, "derived": "A", "label": "T12A"}]
        """
        mapped: list[dict[str, Any]] = []
        for m in mutations:
            mapped.append({
                "pdb_id": pdb_id.upper(),
                "chain": chain,
                "residue_number": m.get("position"),
                "ancestral_aa": m.get("ancestral", ""),
                "derived_aa": m.get("derived", ""),
                "label": m.get("label", f"{m.get('ancestral', '')}{m.get('position')}{m.get('derived', '')}"),
                "color": "#ef4444",  # Red highlight for 3D viewer
            })
        return mapped
