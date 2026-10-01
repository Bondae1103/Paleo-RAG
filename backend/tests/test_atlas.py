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
    assert data["target_locus"]["gene_symbol"] == "COL1A1"
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
    assert "paleobiodb.org/navigator" in fossil["pbdb_navigator_url"]
    assert "paleobiodb.org/data1.2" in fossil["pbdb_api_url"]

