"""
UniProt accession validator: checks whether an accession assigned to a
paleogenomic record is (a) a real, active UniProtKB entry, and (b) biologically
compatible with the organism and gene the record claims it represents.

This sits on top of UniProtClient (live REST calls, caching, rate limiting,
retries all inherited from BioHttpClient) and never fabricates a verdict --
network/API failures surface as status="error", not as a fabricated pass/fail.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from backend.api.bio_schemas import ProteinRecord
from backend.config import Settings, get_settings
from backend.utils.error_types import DatabaseClientError, DatabaseNotFoundError
from backend.utils.http_client import BioHttpClient, get_bio_http_client
from backend.utils.uniprot_client import UniProtClient

logger = logging.getLogger(__name__)

# UniProt "Inactive" entries return entryType == "Inactive" with no organism/sequence.
INACTIVE_ENTRY_TYPE = "Inactive"

# Gene symbol synonyms that should NOT be treated as mismatches (same locus, different alias).
GENE_SYNONYMS: dict[str, set[str]] = {
    "CYTB": {"CYTB", "COB", "MT-CYB", "MTCYB"},
    "COX1": {"COX1", "MT-CO1", "COI", "MTCO1"},
    "ND4L": {"ND4L", "MT-ND4L", "MTND4L", "NADH4L"},
    "HBA": {"HBA", "HBA1", "HBA2", "HBAA"},
    "HBB": {"HBB", "HBB1", "HBB-B1"},
    "COL1A1": {"COL1A1"},
    "NA": {"NA", "NEURAMINIDASE"},
    "HA": {"HA", "HEMAGGLUTININ"},
    "PA": {"PA", "POLYMERASE ACIDIC"},
    "PB2": {"PB2"},
    "PLA": {"PLA"},
    "CAF1": {"CAF1"},
    "YOPM": {"YOPM"},
}


def _normalize_gene(symbol: Optional[str]) -> str:
    return (symbol or "").strip().upper().replace("MT-", "").replace("-", "")


def genes_compatible(expected: Optional[str], actual: list[str]) -> bool:
    """True if `actual` (genes reported by UniProt) plausibly match `expected`."""
    if not expected:
        return True
    exp_norm = _normalize_gene(expected)
    actual_norms = {_normalize_gene(a) for a in actual if a}
    if exp_norm in actual_norms:
        return True
    group = GENE_SYNONYMS.get(expected.strip().upper())
    if group and actual_norms & {_normalize_gene(g) for g in group}:
        return True
    return False


@dataclass
class ValidationVerdict:
    accession: str
    http_status: str  # "ok", "not_found", "inactive", "error"
    reviewed: Optional[bool] = None
    entry_name: Optional[str] = None
    real_organism: Optional[str] = None
    real_taxon_id: Optional[int] = None
    real_gene_symbols: list[str] = field(default_factory=list)
    real_protein_name: Optional[str] = None
    real_sequence_length: Optional[int] = None
    expected_organism: Optional[str] = None
    expected_gene: Optional[str] = None
    organism_match: Optional[bool] = None  # None when unverifiable
    gene_match: Optional[bool] = None
    verdict: str = "unverified"  # see VERDICT_* constants below
    evidence_source: str = "https://rest.uniprot.org/uniprotkb/"
    retrieved_at: Optional[str] = None
    error_message: Optional[str] = None


VERDICT_EXACT_MATCH = "exact_match"
VERDICT_PROXY_SAME_SPECIES = "proxy_same_species"  # e.g. archaic hominin represented by the modern human entry
VERDICT_WRONG_ORGANISM = "wrong_organism"
VERDICT_WRONG_GENE = "wrong_gene"
VERDICT_WRONG_ORGANISM_AND_GENE = "wrong_organism_and_gene"
VERDICT_INACTIVE = "inactive_entry"
VERDICT_INVALID = "invalid_accession"
VERDICT_UNVERIFIED = "unverified"
VERDICT_ERROR = "validation_error"


def _organism_matches(expected: Optional[str], real: Optional[str]) -> Optional[bool]:
    if not expected or not real:
        return None
    exp = expected.strip().lower()
    act = real.strip().lower()
    if exp == act:
        return True
    # Allow genus-level match only if species epithet also shares genus AND
    # caller explicitly wants a loose check -- default is strict equality.
    return False


class UniProtValidator:
    """Validates a (accession, expected_organism, expected_gene) triple against live UniProt."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        http_client: Optional[BioHttpClient] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.http = http_client or get_bio_http_client()
        self.client = UniProtClient(settings=self.settings, http_client=self.http)

    def validate(
        self,
        accession: str,
        expected_organism: Optional[str] = None,
        expected_gene: Optional[str] = None,
        same_species_proxy_organisms: Optional[set[str]] = None,
    ) -> ValidationVerdict:
        """
        same_species_proxy_organisms: a set of organism names (e.g. {"Homo sapiens"})
        for which a mismatch against expected_organism is a KNOWN, legitimate proxy
        (used for extinct hominins with no distinct UniProt entry of their own),
        not an error. Pass None to disable this allowance.
        """
        import datetime

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        acc = accession.strip().upper()

        try:
            record: ProteinRecord = self.client.get_protein(acc)
        except DatabaseNotFoundError:
            return ValidationVerdict(
                accession=acc,
                http_status="not_found",
                expected_organism=expected_organism,
                expected_gene=expected_gene,
                verdict=VERDICT_INVALID,
                retrieved_at=now,
            )
        except DatabaseClientError as exc:
            return ValidationVerdict(
                accession=acc,
                http_status="error",
                expected_organism=expected_organism,
                expected_gene=expected_gene,
                verdict=VERDICT_ERROR,
                retrieved_at=now,
                error_message=str(exc),
            )

        if not record.organism or record.organism == "Unknown organism":
            # UniProt "Inactive" entries parse with no organism/sequence data.
            return ValidationVerdict(
                accession=acc,
                http_status="inactive",
                entry_name=record.entry_name,
                expected_organism=expected_organism,
                expected_gene=expected_gene,
                verdict=VERDICT_INACTIVE,
                retrieved_at=now,
            )

        real_genes = list(record.gene_symbols)

        organism_match = _organism_matches(expected_organism, record.organism)
        is_known_proxy = bool(
            same_species_proxy_organisms
            and record.organism in same_species_proxy_organisms
            and organism_match is False
        )

        gene_match = genes_compatible(expected_gene, real_genes) if real_genes else None

        if is_known_proxy:
            verdict = VERDICT_PROXY_SAME_SPECIES
        elif organism_match is True and (gene_match is True or gene_match is None):
            verdict = VERDICT_EXACT_MATCH
        elif organism_match is False and gene_match is False:
            verdict = VERDICT_WRONG_ORGANISM_AND_GENE
        elif organism_match is False:
            verdict = VERDICT_WRONG_ORGANISM
        elif gene_match is False:
            verdict = VERDICT_WRONG_GENE
        else:
            verdict = VERDICT_UNVERIFIED

        return ValidationVerdict(
            accession=acc,
            http_status="ok",
            reviewed=record.reviewed,
            entry_name=record.entry_name,
            real_organism=record.organism,
            real_taxon_id=record.organism_id,
            real_gene_symbols=real_genes,
            real_protein_name=record.protein_name,
            real_sequence_length=record.length,
            expected_organism=expected_organism,
            expected_gene=expected_gene,
            organism_match=organism_match,
            gene_match=gene_match,
            verdict=verdict,
            retrieved_at=now,
        )
