"""
Functional Annotation & Interaction Client:
Pfam (via InterPro), PROSITE regex motif miner, Gene Ontology (GO), KEGG pathways,
and STRING DB protein-protein interaction networks (with graceful BioGRID fallback).
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

from backend.api.bio_schemas import DomainHit, InteractionEdge, PathwayHit
from backend.config import Settings, get_settings
from backend.utils.error_types import DatabaseClientError, DatabaseNotFoundError
from backend.utils.http_client import BioHttpClient, get_bio_http_client

logger = logging.getLogger(__name__)


def prosite_to_regex(pattern_str: str) -> str:
    """
    Convert standard PROSITE pattern syntax into Python regex:
    - [ALT] becomes [ALT]
    - {AM} becomes [^AM] (any amino acid except A or M)
    - x becomes [A-Z]
    - x(3) becomes [A-Z]{3}
    - x(2,4) becomes [A-Z]{2,4}
    - Hyphens '-' stripped (before inserting [A-Z] ranges)
    - '<' at start becomes '^'
    - '>' at end becomes '$'
    """
    p = pattern_str.strip()
    if p.endswith("."):
        p = p[:-1]

    # Handle N-terminal < and C-terminal >
    start_anchor = "^" if p.startswith("<") else ""
    if p.startswith("<"):
        p = p[1:]
    end_anchor = "$" if p.endswith(">") else ""
    if p.endswith(">"):
        p = p[:-1]

    # First remove hyphens between PROSITE tokens (hyphens are strictly token delimiters)
    p = p.replace("-", "")

    # Replace excluded sets {AM} with [^AM]
    p = re.sub(r"\{([A-Z]+)\}", r"[^\1]", p)

    # Replace x(N,M) with [A-Z]{N,M} and x(N) with [A-Z]{N}
    p = re.sub(r"x\((\d+),(\d+)\)", r"[A-Z]{\1,\2}", p)
    p = re.sub(r"x\((\d+)\)", r"[A-Z]{\1}", p)
    p = re.sub(r"x", r"[A-Z]", p)

    return f"{start_anchor}{p}{end_anchor}"


# Standard curated paleogenomic PROSITE signatures
KNOWN_PROSITE_PATTERNS = {
    "PS01033": {
        "name": "GLOBIN_HEME",
        "description": "Globin family proximal/distal heme pocket signature",
        "pattern": "[LIVMF]-x-H-[LIVMFY]",
    },
    "PS00658": {
        "name": "FORK_HEAD_2",
        "description": "Forkhead domain signature 2 (FOXP2)",
        "pattern": "W-[QKR]-[NSD]-[SA]-[LIV]-R-H",
    },
    "PS00834": {
        "name": "OMPTIN_1",
        "description": "Omptin family signature 1 (Yersinia Pla protease)",
        "pattern": "W-T-D-x-S-x-H-P-x-T",
    },
    "COLLAGEN_REPEAT": {
        "name": "COLLAGEN_GLY_X_Y",
        "description": "Collagen triple-helix Gly-X-Y repeat motif",
        "pattern": "G-x(2)-G-x(2)-G",
    },
    "PS00017": {
        "name": "ATP_GTP_P_LOOP",
        "description": "ATP/GTP-binding site motif A (P-loop)",
        "pattern": "[AG]-x(4)-G-K-[ST]",
    },
}


class FunctionalClient:
    """Client for Pfam (InterPro), PROSITE, GO, KEGG, and STRING DB."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        http_client: Optional[BioHttpClient] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.http = http_client or get_bio_http_client()
        self.interpro_base = self.settings.interpro_api_base.rstrip("/")
        self.string_base = self.settings.string_api_base.rstrip("/")
        self.kegg_base = self.settings.kegg_api_base.rstrip("/")

    # ----------------------------------------------------
    # PROSITE LOCAL REGEX MINING
    # ----------------------------------------------------
    def scan_prosite_motifs(self, sequence: str) -> list[DomainHit]:
        """Scan sequence with local PROSITE regex signatures (offline capable)."""
        clean_seq = re.sub(r"[\s\d\->]", "", sequence).upper()
        hits: list[DomainHit] = []

        for pid, meta in KNOWN_PROSITE_PATTERNS.items():
            regex_str = prosite_to_regex(meta["pattern"])
            pattern = re.compile(regex_str)
            for m in pattern.finditer(clean_seq):
                hits.append(
                    DomainHit(
                        id=pid,
                        database="PROSITE",
                        name=meta["name"],
                        description=f"{meta['description']} (match: {m.group(0)})",
                        start=m.start() + 1,
                        end=m.end(),
                    )
                )

        return hits

    # ----------------------------------------------------
    # PFAM / INTERPRO DOMAINS
    # ----------------------------------------------------
    def get_pfam_domain(self, pfam_id: str) -> Optional[DomainHit]:
        """Fetch Pfam domain metadata from InterPro API."""
        clean_id = pfam_id.strip().upper()
        url = f"{self.interpro_base}/entry/pfam/{clean_id}"
        try:
            data = self.http.get_json(url)
            metadata = data.get("metadata", {})
            name = metadata.get("name", {}).get("name", clean_id)
            desc = metadata.get("description", [{}])[0].get("text", "")
            return DomainHit(
                id=clean_id,
                database="Pfam",
                name=name,
                description=desc,
                start=1,
                end=1,
            )
        except Exception:
            return None

    # ----------------------------------------------------
    # KEGG PATHWAYS
    # ----------------------------------------------------
    def get_kegg_pathway(self, pathway_id: str) -> Optional[PathwayHit]:
        """Fetch KEGG pathway details (e.g. map05100)."""
        clean_id = pathway_id.strip()
        if not clean_id.startswith("map") and not clean_id.startswith("path:"):
            clean_id = f"map{clean_id}"
        if clean_id.startswith("path:"):
            clean_id = clean_id.replace("path:", "")

        url = f"{self.kegg_base}/get/{clean_id}"
        try:
            text = self.http.get_text(url)
            name = clean_id
            desc = ""
            for line in text.splitlines():
                if line.startswith("NAME"):
                    name = line.replace("NAME", "").strip()
                elif line.startswith("DESCRIPTION"):
                    desc = line.replace("DESCRIPTION", "").strip()
            return PathwayHit(
                pathway_id=clean_id,
                name=name,
                database="KEGG",
                url=f"https://www.kegg.jp/pathway/{clean_id}",
                description=desc or None,
            )
        except Exception:
            return None

    # ----------------------------------------------------
    # STRING PROTEIN INTERACTIONS
    # ----------------------------------------------------
    def get_string_interactions(
        self,
        identifier: str,
        species: int = 9606,  # 9606 = Homo sapiens default
        limit: int = 10,
        min_score: int = 400,
    ) -> list[InteractionEdge]:
        """
        Query STRING DB REST API for functional protein-protein interaction network.
        Includes evidence channels: experimental, database, coexpression, textmining.
        """
        url = f"{self.string_base}/json/network"
        try:
            data = self.http.get_json(
                url,
                params={
                    "identifiers": identifier,
                    "species": species,
                    "limit": limit,
                    "required_score": min_score,
                },
            )
            edges: list[InteractionEdge] = []
            for item in data:
                edges.append(
                    InteractionEdge(
                        source=item.get("preferredName_A", item.get("stringId_A", "")),
                        target=item.get("preferredName_B", item.get("stringId_B", "")),
                        score=float(item.get("score", 0.0)),
                        evidence_channels={
                            "experimental": float(item.get("escore", 0.0)),
                            "database": float(item.get("dscore", 0.0)),
                            "coexpression": float(item.get("ascore", 0.0)),
                            "textmining": float(item.get("tscore", 0.0)),
                            "neighborhood": float(item.get("nscore", 0.0)),
                        },
                    )
                )
            return edges
        except Exception as exc:
            logger.warning(f"STRING interaction lookup failed for {identifier}: {exc}")
            return []

    # ----------------------------------------------------
    # BIOGRID INTERACTION CLIENT (WITH GRACEFUL FALLBACK)
    # ----------------------------------------------------
    def get_biogrid_interactions(self, gene_symbol: str) -> list[InteractionEdge]:
        """Query BioGRID if API key is configured; fallback gracefully if omitted."""
        if not self.settings.biogrid_api_key:
            logger.debug("BIOGRID_API_KEY not configured; skipping BioGRID query.")
            return []

        url = f"{self.settings.biogrid_api_base.rstrip('/')}/interactions"
        try:
            data = self.http.get_json(
                url,
                params={
                    "searchNames": "true",
                    "geneList": gene_symbol,
                    "taxId": 9606,
                    "format": "json",
                    "accesskey": self.settings.biogrid_api_key,
                },
            )
            edges: list[InteractionEdge] = []
            for _, item in data.items():
                edges.append(
                    InteractionEdge(
                        source=item.get("OFFICIAL_SYMBOL_A", ""),
                        target=item.get("OFFICIAL_SYMBOL_B", ""),
                        score=0.9,
                        evidence_channels={"biogrid_experimental": 1.0},
                    )
                )
            return edges
        except Exception as exc:
            logger.warning(f"BioGRID query failed: {exc}")
            return []
