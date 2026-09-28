"""
NCBI E-utilities client for nucleotide, gene, and mitochondrial genome retrieval.
Uses BioHttpClient for caching, rate limiting, and NCBI etiquette (tool/email/api_key).
"""
from __future__ import annotations

import io
import logging
from typing import Any, Optional

from Bio import SeqIO

from backend.api.bio_schemas import SequenceFeature, SequenceRecord, SequenceType
from backend.config import Settings, get_settings
from backend.utils.error_types import DatabaseClientError, DatabaseNotFoundError
from backend.utils.http_client import BioHttpClient, get_bio_http_client
from backend.utils.sequence_tools import detect_sequence_type, validate_sequence

logger = logging.getLogger(__name__)


class NCBIClient:
    """Client for NCBI Entrez E-utilities (nuccore / gene / popset)."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        http_client: Optional[BioHttpClient] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.http = http_client or get_bio_http_client()
        self.base_url = self.settings.ncbi_eutils_base.rstrip("/")

    def search_nucleotide(self, term: str, retmax: int = 10) -> list[str]:
        """Search NCBI Nucleotide (nuccore) and return UIDs."""
        url = f"{self.base_url}/esearch.fcgi"
        data = self.http.get_json(
            url,
            params={
                "db": "nuccore",
                "term": term,
                "retmax": retmax,
                "retmode": "json",
            },
        )
        id_list = data.get("esearchresult", {}).get("idlist", [])
        return id_list

    def get_summary(self, uid_or_acc: str) -> dict[str, Any]:
        """Fetch docsum metadata for a nucleotide UID or accession."""
        url = f"{self.base_url}/esummary.fcgi"
        data = self.http.get_json(
            url,
            params={
                "db": "nuccore",
                "id": uid_or_acc,
                "retmode": "json",
            },
        )
        result = data.get("result", {})
        uids = result.get("uids", [])
        if uids:
            return result.get(uids[0], {})
        return {}

    def fetch_fasta(self, accession: str) -> str:
        """Fetch raw FASTA format text from NCBI Nucleotide."""
        url = f"{self.base_url}/efetch.fcgi"
        text = self.http.get_text(
            url,
            params={
                "db": "nuccore",
                "id": accession,
                "rettype": "fasta",
                "retmode": "text",
            },
        )
        if not text or not text.strip().startswith(">"):
            raise DatabaseNotFoundError(f"Accession {accession} not found in NCBI Nucleotide.", database="ncbi")
        return text

    def fetch_genbank(self, accession: str) -> str:
        """Fetch raw GenBank flatfile text from NCBI Nucleotide."""
        url = f"{self.base_url}/efetch.fcgi"
        text = self.http.get_text(
            url,
            params={
                "db": "nuccore",
                "id": accession,
                "rettype": "gb",
                "retmode": "text",
            },
        )
        if not text or "LOCUS" not in text:
            raise DatabaseNotFoundError(f"Accession {accession} not found in NCBI Nucleotide.", database="ncbi")
        return text

    def get_sequence_record(self, accession: str) -> SequenceRecord:
        """Fetch, parse, and normalize nucleotide record into SequenceRecord schema."""
        gb_text = self.fetch_genbank(accession)
        try:
            stream = io.StringIO(gb_text)
            parsed_rec = next(SeqIO.parse(stream, "genbank"))
        except Exception as exc:
            logger.warning(f"GenBank parsing failed for {accession}: {exc}, falling back to FASTA")
            fasta_text = self.fetch_fasta(accession)
            stream = io.StringIO(fasta_text)
            parsed_rec = next(SeqIO.parse(stream, "fasta"))

        seq_str = str(parsed_rec.seq).upper()
        seq_type = detect_sequence_type(seq_str)
        val = validate_sequence(seq_str, expected_type=seq_type)

        features: list[SequenceFeature] = []
        for feat in getattr(parsed_rec, "features", []):
            features.append(
                SequenceFeature(
                    type=feat.type,
                    location=str(feat.location),
                    qualifiers={k: v if isinstance(v, list) else [str(v)] for k, v in feat.qualifiers.items()},
                )
            )

        return SequenceRecord(
            id=parsed_rec.id or accession,
            name=parsed_rec.name or accession,
            description=parsed_rec.description or "",
            sequence=seq_str,
            length=len(seq_str),
            seq_type=seq_type,
            gc_content=val.gc_percent,
            molecular_weight_kda=val.molecular_weight_kda,
            ambiguity_index=val.ambiguity_index,
            features=features,
            annotations={k: str(v) for k, v in parsed_rec.annotations.items()},
        )
