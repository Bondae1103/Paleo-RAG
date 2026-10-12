"""
Regression tests for the UniProt accession audit (backend/utils/uniprot_validator.py)
and for the corrected paleo_atlas_registry.json data itself.

These guard against the exact failure mode that prompted the audit: a real,
resolvable UniProt accession silently reused across unrelated taxa/genes.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import respx
import httpx

from backend.utils.http_client import BioHttpClient, DiskCache
from backend.utils.uniprot_validator import (
    UniProtValidator,
    genes_compatible,
    VERDICT_EXACT_MATCH,
    VERDICT_PROXY_SAME_SPECIES,
    VERDICT_WRONG_ORGANISM,
    VERDICT_WRONG_GENE,
    VERDICT_WRONG_ORGANISM_AND_GENE,
    VERDICT_INACTIVE,
    VERDICT_INVALID,
    VERDICT_ERROR,
)

REGISTRY_PATH = Path(__file__).parent.parent / "data" / "paleo_atlas_registry.json"


def _mock_entry(accession: str, organism: str, taxon_id: int, gene: str, protein_name: str, sequence: str) -> dict:
    return {
        "primaryAccession": accession,
        "uniProtkbId": f"{gene}_{organism.split()[0].upper()}",
        "entryType": "UniProtKB reviewed (Swiss-Prot)",
        "proteinDescription": {"recommendedName": {"fullName": {"value": protein_name}}},
        "organism": {"scientificName": organism, "taxonId": taxon_id},
        "sequence": {"value": sequence, "length": len(sequence)},
        "genes": [{"geneName": {"value": gene}}],
        "features": [],
        "uniProtKBCrossReferences": [],
    }


LION_CYTB = _mock_entry("Q35506", "Panthera leo", 9689, "CYTB", "Cytochrome b", "M" * 379)
HUMAN_ND4L = _mock_entry("P03901", "Homo sapiens", 9606, "MT-ND4L", "NADH-ubiquinone oxidoreductase chain 4L", "M" * 98)
HUMAN_FOXP2 = _mock_entry("O15409", "Homo sapiens", 9606, "FOXP2", "Forkhead box protein P2", "M" * 715)


class TestGenesCompatible:
    def test_exact_symbol_matches(self):
        assert genes_compatible("CYTB", ["CYTB"]) is True

    def test_known_synonym_matches(self):
        assert genes_compatible("CYTB", ["MT-CYB"]) is True

    def test_unrelated_gene_does_not_match(self):
        assert genes_compatible("CYTB", ["MT-ND4L"]) is False

    def test_no_expectation_is_always_compatible(self):
        assert genes_compatible(None, ["ANYTHING"]) is True


@pytest.fixture
def validator(tmp_path):
    """A validator with its own isolated disk cache, so one test's cached
    response can never shadow another test's respx mock for the same accession."""
    http = BioHttpClient(cache=DiskCache(cache_dir=tmp_path))
    return UniProtValidator(http_client=http)


class TestUniProtValidator:
    @respx.mock
    def test_detects_wrong_organism_and_gene(self, validator):
        """The exact failure mode reported: P03901 (human MT-ND4L) mislabeled as a big cat's CYTB."""
        respx.get("https://rest.uniprot.org/uniprotkb/P03901.json").respond(200, json=HUMAN_ND4L)
        result = validator.validate("P03901", expected_organism="Panthera leo", expected_gene="CYTB")
        assert result.verdict == VERDICT_WRONG_ORGANISM_AND_GENE
        assert result.real_organism == "Homo sapiens"
        assert result.organism_match is False
        assert result.gene_match is False

    @respx.mock
    def test_exact_match_for_correct_species_and_gene(self, validator):
        respx.get("https://rest.uniprot.org/uniprotkb/Q35506.json").respond(200, json=LION_CYTB)
        result = validator.validate("Q35506", expected_organism="Panthera leo", expected_gene="CYTB")
        assert result.verdict == VERDICT_EXACT_MATCH
        assert result.organism_match is True
        assert result.gene_match is True

    @respx.mock
    def test_wrong_organism_only_when_gene_matches(self, validator):
        """Same gene family, but it's a different species' entry -- still a real finding."""
        respx.get("https://rest.uniprot.org/uniprotkb/O15409.json").respond(200, json=HUMAN_FOXP2)
        result = validator.validate("O15409", expected_organism="Pan troglodytes", expected_gene="FOXP2")
        assert result.verdict == VERDICT_WRONG_ORGANISM
        assert result.gene_match is True
        assert result.organism_match is False

    @respx.mock
    def test_known_proxy_is_not_flagged_as_an_error(self, validator):
        """A human accession used for an extinct hominin with no UniProt entry of its own
        is a documented, legitimate convention -- must not be treated as a mismatch."""
        respx.get("https://rest.uniprot.org/uniprotkb/O15409.json").respond(200, json=HUMAN_FOXP2)
        result = validator.validate(
            "O15409",
            expected_organism="Homo neanderthalensis",
            expected_gene="FOXP2",
            same_species_proxy_organisms={"Homo sapiens"},
        )
        assert result.verdict == VERDICT_PROXY_SAME_SPECIES

    @respx.mock
    def test_inactive_entry_is_unverifiable_not_guessed(self, validator):
        respx.get("https://rest.uniprot.org/uniprotkb/Q96SF8.json").respond(
            200, json={"entryType": "Inactive", "primaryAccession": "Q96SF8", "uniProtkbId": "Q96SF8_HUMAN"}
        )
        result = validator.validate("Q96SF8", expected_organism="Homo sapiens denisova", expected_gene="TBX15")
        assert result.verdict == VERDICT_INACTIVE
        assert result.real_organism is None

    @respx.mock
    def test_unknown_accession_is_invalid_not_fabricated(self, validator):
        respx.get("https://rest.uniprot.org/uniprotkb/ZZZZZZ.json").respond(404)
        result = validator.validate("ZZZZZZ", expected_organism="Panthera leo", expected_gene="CYTB")
        assert result.verdict == VERDICT_INVALID
        assert result.real_organism is None

    @respx.mock
    def test_api_failure_surfaces_as_error_not_as_a_silent_pass(self, validator):
        respx.get("https://rest.uniprot.org/uniprotkb/P03901.json").mock(
            side_effect=httpx.ConnectError("network unreachable")
        )
        result = validator.validate("P03901", expected_organism="Panthera leo", expected_gene="CYTB")
        assert result.verdict == VERDICT_ERROR
        assert result.real_organism is None
        assert result.error_message


@pytest.mark.skipif(not REGISTRY_PATH.exists(), reason="registry data file not present")
class TestCorrectedRegistryIntegrity:
    """Guards the corrected dataset itself: no silent cross-taxon accession reuse,
    full provenance on every corrected/unverified field, no fabricated placeholders."""

    @pytest.fixture(scope="class")
    @classmethod
    def registry(cls):
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    def _iter_sites(self, registry):
        for entry in registry:
            tl = entry.get("target_locus", {})
            yield entry["tax_id"], tl.get("extinct_uniprot_acc"), entry.get("scientific_name"), tl.get("extinct_uniprot_validation")
            ec = entry.get("extant_counterpart", {})
            yield entry["tax_id"], ec.get("extant_uniprot_acc"), ec.get("scientific_name"), ec.get("extant_uniprot_validation")
            for s in entry.get("molecular_samples", []):
                yield entry["tax_id"], s.get("extinct_uniprot_acc"), entry.get("scientific_name"), s.get("extinct_uniprot_validation")
                ec2 = s.get("extant_counterpart", {})
                yield entry["tax_id"], ec2.get("extant_uniprot_acc"), ec2.get("scientific_name"), ec2.get("extant_uniprot_validation")

    def test_no_accession_is_reused_across_distinct_unvalidated_organisms(self, registry):
        """A live, resolvable accession may legitimately appear for >1 taxon only when
        the organisms are identical, or the reuse is an explicitly recorded proxy."""
        by_acc: dict[str, set[str]] = {}
        proxy_accs: set[str] = set()
        for _, acc, organism, validation in self._iter_sites(registry):
            if not acc:
                continue
            by_acc.setdefault(acc, set()).add(organism)
            if validation and validation.get("status") == "verified_proxy":
                proxy_accs.add(acc)
        offenders = {acc: orgs for acc, orgs in by_acc.items() if len(orgs) > 1 and acc not in proxy_accs}
        assert offenders == {}, f"Accessions reused across different, non-proxy organisms: {offenders}"

    def test_every_populated_accession_has_validation_provenance(self, registry):
        missing = []
        for tax_id, acc, organism, validation in self._iter_sites(registry):
            if acc and not validation:
                missing.append((tax_id, acc, organism))
        assert missing == [], f"Accessions with no recorded validation provenance: {missing}"

    def test_every_nulled_accession_is_marked_unverified_with_a_reason(self, registry):
        for tax_id, acc, organism, validation in self._iter_sites(registry):
            if acc is None and validation is not None:
                assert validation.get("status") == "unverified", (tax_id, organism, validation)
                assert validation.get("note"), f"Unverified record with no explanatory note: {tax_id}/{organism}"

    def test_no_fabricated_taxon_id_placeholder_remains(self, registry):
        """organism_id 99999 was the smoking-gun placeholder for fabricated records."""
        raw = json.dumps(registry)
        assert "99999" not in raw
