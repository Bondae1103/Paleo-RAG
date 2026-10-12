"""
Unit tests for PaleoRAG Taxa Atlas & Evolutionary Registry endpoints.
"""
import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_atlas_catalog_returns_all_taxa():
    resp = client.get("/api/bio/atlas")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_taxa" in data
    assert data["total_taxa"] >= 18
    assert len(data["catalog"]) >= 18

    first = data["catalog"][0]
    assert "tax_id" in first
    assert "scientific_name" in first
    assert "target_locus" in first
    assert "extant_counterpart" in first
    assert "structure" in first


def test_atlas_catalog_filters_by_clade():
    resp = client.get("/api/bio/atlas?clade=Carnivora")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_taxa"] >= 3
    for entry in data["catalog"]:
        assert "carnivora" in entry["clade"].lower()


def test_atlas_get_taxon_by_id():
    resp = client.get("/api/bio/atlas/PRAG-TAX-010")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tax_id"] == "PRAG-TAX-010"
    assert "Smilodon" in data["scientific_name"]
    assert data["target_locus"]["gene_symbol"] in ("COL1A1", "CYTB")
    assert data["extant_counterpart"]["scientific_name"] == "Neofelis nebulosa"
    assert len(data["structure"]["mutations"]) > 0


def test_atlas_get_taxon_by_alias():
    resp = client.get("/api/bio/atlas/Mammoth")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tax_id"] == "PRAG-TAX-001"
    assert "Mammuthus" in data["scientific_name"]


def test_atlas_get_taxon_not_found():
    resp = client.get("/api/bio/atlas/UNKNOWN_TAXON_99999")
    assert resp.status_code == 404


def test_atlas_taxon_fossil_record_from_pbdb():
    resp = client.get("/api/bio/atlas/PRAG-TAX-001")
    assert resp.status_code == 200
    data = resp.json()
    assert "fossil_record" in data
    fossil = data["fossil_record"]
    assert fossil is not None
    assert fossil["pbdb_taxon_id"] == "txn:46027"
    assert fossil["fossil_occurrences_count"] == 77
    # The PaleoBioDB link must open this taxon's own record, not the
    # Navigator app's generic homepage.
    assert fossil["pbdb_navigator_url"] == "https://paleobiodb.org/classic/checkTaxonInfo?taxon_no=46027"
    assert "paleobiodb.org/data1.2" in fossil["pbdb_api_url"]


def test_atlas_pbdb_link_is_taxon_specific_for_every_taxon_with_a_record():
    """Every taxon with a known PBDB taxon_id must link to that taxon's own
    classic/checkTaxonInfo record, never the Navigator app's generic
    homepage -- and a taxon genuinely absent from PBDB (bacteria, viruses)
    must not get a fabricated link."""
    resp = client.get("/api/bio/atlas")
    assert resp.status_code == 200
    for entry in resp.json()["catalog"]:
        fossil = entry.get("fossil_record")
        if not fossil:
            continue
        taxon_id = fossil.get("pbdb_taxon_id")
        url = fossil.get("pbdb_navigator_url")
        if taxon_id:
            numeric_id = taxon_id.split(":", 1)[-1]
            assert url == f"https://paleobiodb.org/classic/checkTaxonInfo?taxon_no={numeric_id}"
        else:
            assert url is None


def test_atlas_yersinia_pestis_kegg_pathways_are_live_verified():
    """Regression guard: map05100 ('Bacterial invasion of epithelial cells')
    was previously misapplied to every Yersinia pestis gene. pla/caf1 have
    no live-confirmed KEGG pathway (must be null); yopM is a true member of
    map05135 ('Yersinia infection'), not map05130 ('Pathogenic E. coli
    infection', a different species' pathway)."""
    resp = client.get("/api/bio/atlas/PRAG-TAX-003")
    assert resp.status_code == 200
    data = resp.json()
    samples = {s["gene_symbol"]: s for s in data["molecular_samples"]}
    assert samples["pla"]["pathway"]["kegg_id"] is None
    assert samples["caf1"]["pathway"]["kegg_id"] is None
    assert samples["yopM"]["pathway"]["kegg_id"] == "map05135"


def test_atlas_mammoth_hbb_nucleotide_accession_not_wrong_organism():
    """Regression guard: HQ184444.1 (an uncultured xanthophyte chloroplast
    gene, not mammoth hemoglobin) must never be served again for Mammuthus
    primigenius HBB; an unverifiable accession must be null, not a guess."""
    resp = client.get("/api/bio/atlas/PRAG-TAX-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["target_locus"]["extinct_nucleotide_acc"] != "HQ184444.1"
    assert data["target_locus"]["extinct_nucleotide_acc"] is None
    assert data["target_locus"]["extinct_nucleotide_validation"]["status"] == "unverified"


def test_atlas_ensembl_locus_never_mixes_organisms():
    """Every non-null genomics block's ensembl_species must be internally
    consistent with its own molecular sample's declared extant_counterpart
    organism -- the registry previously had samples pointing their Ensembl
    link at a different species' genome than the one the sample claimed to
    represent (e.g. a Dromaius novaehollandiae sample linking to Struthio
    camelus coordinates)."""
    resp = client.get("/api/bio/atlas")
    assert resp.status_code == 200
    for entry in resp.json()["catalog"]:
        for sample in entry.get("molecular_samples") or []:
            genomics = sample.get("genomics") or {}
            if not genomics.get("chromosome"):
                continue  # unresolved -- nothing to check
            extant_org = sample["extant_counterpart"]["scientific_name"]
            slug = (genomics.get("ensembl_species") or "").replace("_", " ").lower()
            assert slug.startswith(extant_org.lower()) or extant_org.lower().startswith(slug.split(" (")[0])

