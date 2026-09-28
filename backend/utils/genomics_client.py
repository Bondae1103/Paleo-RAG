"""
Comparative Genomics & Locus Linker (Module 6):
Ensembl REST client for orthologs and synteny, UCSC Genome Browser track link generator,
and NCBI GEO accession resolver.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from backend.api.bio_schemas import LocusLink
from backend.config import Settings, get_settings
from backend.utils.http_client import BioHttpClient, get_bio_http_client

logger = logging.getLogger(__name__)

# Known paleogenomic comparative loci
PALEOGENOMIC_LOCI = {
    "FOXP2": {
        "chromosome": "chr7",
        "start": 114055052,
        "end": 114693772,
        "assembly": "GRCh38",
        "species": "Homo sapiens",
        "notes": "Altai Neanderthal shared derived substitutions (T303N, N325S)",
    },
    "HBB": {
        "chromosome": "chr11",
        "start": 5225464,
        "end": 5227071,
        "assembly": "GRCh38",
        "species": "Homo sapiens / Mammuthus primigenius orthology",
        "notes": "Syntenic with Asian Elephant (Elephas maximus) chromosome 16",
    },
}


class GenomicsClient:
    """Client for Ensembl REST, UCSC Genome Browser tracks, and GEO linkage."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        http_client: Optional[BioHttpClient] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.http = http_client or get_bio_http_client()
        self.ensembl_base = self.settings.ensembl_api_base.rstrip("/")

    def get_gene_locus(self, gene_symbol: str, species: str = "human") -> Optional[LocusLink]:
        """Fetch gene coordinates from Ensembl REST or fallback to curated paleogenomic table."""
        clean_symbol = gene_symbol.strip().upper()
        url = f"{self.ensembl_base}/lookup/symbol/{species}/{clean_symbol}"

        try:
            data = self.http.get_json(url, headers={"Content-Type": "application/json"})
            chrom = str(data.get("seq_region_name", "1"))
            if not chrom.startswith("chr"):
                chrom = f"chr{chrom}"
            start = int(data.get("start", 1))
            end = int(data.get("end", 1))
            assembly = data.get("assembly_name", "GRCh38")

            return LocusLink(
                gene_symbol=clean_symbol,
                species=species,
                chromosome=chrom,
                start=start,
                end=end,
                assembly=assembly,
                ensembl_url=f"https://www.ensembl.org/{species}/Gene/Summary?g={data.get('id', clean_symbol)}",
                ucsc_url=self.generate_ucsc_link(chrom, start, end, assembly=assembly, include_archaic_tracks=True),
            )
        except Exception as exc:
            logger.debug(f"Ensembl query failed for {gene_symbol}: {exc}")
            # Fallback to curated paleogenomic loci
            if clean_symbol in PALEOGENOMIC_LOCI:
                info = PALEOGENOMIC_LOCI[clean_symbol]
                return LocusLink(
                    gene_symbol=clean_symbol,
                    species=info["species"],
                    chromosome=info["chromosome"],
                    start=info["start"],
                    end=info["end"],
                    assembly=info["assembly"],
                    ensembl_url=f"https://www.ensembl.org/Homo_sapiens/Gene/Summary?g={clean_symbol}",
                    ucsc_url=self.generate_ucsc_link(
                        info["chromosome"],
                        info["start"],
                        info["end"],
                        assembly=info["assembly"],
                        include_archaic_tracks=True,
                    ),
                )
            return None

    def generate_ucsc_link(
        self,
        chromosome: str,
        start: int,
        end: int,
        assembly: str = "hg38",
        include_archaic_tracks: bool = True,
    ) -> str:
        """
        Generate deep-link to UCSC Human Genome Browser Gateway with
        Altai Neanderthal and Denisovan high-coverage BAM/VCF tracks enabled.
        """
        db = "hg38" if "38" in assembly else "hg19"
        pos = f"{chromosome}:{start}-{end}"
        base = f"https://genome.ucsc.edu/cgi-bin/hgTracks?db={db}&position={pos}"
        if include_archaic_tracks and db == "hg38":
            base += "&neandAltai=pack&denisova=pack"
        return base

    def format_geo_link(self, geo_accession: str) -> str:
        """Format NCBI Gene Expression Omnibus (GEO) browser URL."""
        clean_acc = geo_accession.strip().upper()
        return f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={clean_acc}"
