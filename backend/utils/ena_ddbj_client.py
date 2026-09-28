"""
ENA (European Nucleotide Archive) and DDBJ (DNA Data Bank of Japan) integration client.
Documents and leverages INSDC cross-mirroring across GenBank, ENA, and DDBJ.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from backend.api.bio_schemas import SequenceRecord, SequenceType
from backend.config import Settings, get_settings
from backend.utils.error_types import DatabaseNotFoundError
from backend.utils.http_client import BioHttpClient, get_bio_http_client
from backend.utils.sequence_tools import detect_sequence_type, validate_sequence

logger = logging.getLogger(__name__)


class EnaDdbjClient:
    """
    Client for ENA Portal/Browser API and INSDC DDBJ cross-referencing.
    INSDC Note: The International Nucleotide Sequence Database Collaboration (INSDC)
    synchronizes data daily between NCBI GenBank, EMBL-EBI/ENA, and DDBJ.
    Any DDBJ accession (e.g. AB*, LC*, BR*) or ENA accession (e.g. AL*, FJ*)
    is addressable via both the ENA REST portal and NCBI E-utilities.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        http_client: Optional[BioHttpClient] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.http = http_client or get_bio_http_client()
        self.ena_browser_base = "https://www.ebi.ac.uk/ena/browser/api"
        self.ena_portal_base = self.settings.ena_api_base.rstrip("/")

    def fetch_ena_fasta(self, accession: str) -> str:
        """Fetch FASTA from ENA Browser API."""
        url = f"{self.ena_browser_base}/fasta/{accession}"
        try:
            text = self.http.get_text(url)
            if not text or not text.strip().startswith(">"):
                raise DatabaseNotFoundError(f"Accession {accession} not found in ENA.", database="ena")
            return text
        except Exception as exc:
            raise DatabaseNotFoundError(f"ENA lookup failed for {accession}: {exc}", database="ena")

    def get_filereport(self, accession: str) -> list[dict[str, Any]]:
        """Retrieve ENA Portal metadata report (reads, runs, or assemblies)."""
        url = f"{self.ena_portal_base}/filereport"
        try:
            data = self.http.get_text(
                url,
                params={
                    "accession": accession,
                    "result": "read_run",
                    "fields": "study_accession,sample_accession,experiment_accession,run_accession,tax_id,scientific_name,base_count",
                    "format": "tsv",
                },
            )
            lines = data.strip().splitlines()
            if len(lines) <= 1:
                return []
            header = lines[0].split("\t")
            rows = []
            for line in lines[1:]:
                parts = line.split("\t")
                rows.append(dict(zip(header, parts)))
            return rows
        except Exception:
            return []

    def get_sequence_record(self, accession: str) -> SequenceRecord:
        """Retrieve sequence from ENA and normalize into SequenceRecord schema."""
        fasta_text = self.fetch_ena_fasta(accession)
        lines = fasta_text.strip().splitlines()
        header = lines[0][1:] if lines else accession
        seq_str = "".join(lines[1:]).upper()

        st = detect_sequence_type(seq_str)
        val = validate_sequence(seq_str, expected_type=st)

        return SequenceRecord(
            id=accession,
            name=header.split()[0] if header else accession,
            description=header,
            sequence=seq_str,
            length=len(seq_str),
            seq_type=st,
            gc_content=val.gc_percent,
            molecular_weight_kda=val.molecular_weight_kda,
            ambiguity_index=val.ambiguity_index,
            annotations={"source_database": "ENA/INSDC", "mirrored_from": "DDBJ/EMBL"},
        )
