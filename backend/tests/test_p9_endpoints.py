import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_p9_atlas_taxon_proteins():
    # Test mammoth PRAG-TAX-001
    resp = client.get("/api/bio/atlas/PRAG-TAX-001/proteins?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tax_id"] == "PRAG-TAX-001"
    assert data["total_proteins"] > 0
    assert len(data["proteins"]) > 0
    first = data["proteins"][0]
    assert "accession" in first
    assert "gene_symbol" in first
    assert "reviewed" in first

def test_p9_protein_details_crystal_and_synteny():
    # D3U1H8 (Woolly Mammoth Hemoglobin subunit alpha)
    resp = client.get("/api/bio/protein/D3U1H8/details")
    assert resp.status_code == 200
    data = resp.json()
    assert data["accession"] == "D3U1H8"
    assert "Mammuthus primigenius" in data["organism_name"]
    assert len(data["experimental_structures"]) > 0
    # Check SIFTS mapping residue fields
    assert "uniprot_start" in data["experimental_structures"][0]
    assert "uniprot_end" in data["experimental_structures"][0]
    # Check Extant orthology synteny
    assert data["orthology"] is not None
    assert data["orthology"]["extant_common_name"] == "African elephant"
    assert data["orthology"]["extant_gene_symbol"] == "HBA1"
    assert "extant_neighborhood" in data["orthology"]
    # Check Cross references grouped
    assert "cross_references" in data
    # Check Papers
    assert len(data["papers"]) > 0

def test_p9_protein_rag_summary():
    resp = client.get("/api/bio/protein/D3U1H8/rag-summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["accession"] == "D3U1H8"
    assert "explanation" in data
    assert "abstention" in data

def test_p9_pbdb_proxy():
    # Test PBDB proxy for Mammuthus primigenius taxon_no 47867
    resp = client.get("/api/bio/pbdb/proxy/47867")
    assert resp.status_code == 200
    data = resp.json()
    assert "records" in data or "taxon_no" in data or "status" in data

def test_p9_diagnostics_metrics():
    resp = client.get("/api/bio/diagnostics/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["database"]["taxa_count"] == 18
    assert data["database"]["proteins_count"] == 5626
    assert data["database"]["structures_mapped_count"] == 2699
    assert data["database"]["sifts_residue_coverage_pct"] == 100.0
    assert data["database"]["cross_references_count"] == 101032
    assert data["database"]["predicted_structures_count"] == 355
    assert data["database"]["papers_count"] == 885
    assert data["database"]["open_access_papers_count"] == 443
    assert data["database"]["extant_orthologs_count"] == 5627
    assert data["rag"]["collection_name"] == "paleo_chunks"
    assert data["rag"]["total_semantic_chunks"] == 6393
    assert data["rag"]["benchmark"]["total_questions"] == 23
    assert data["rag"]["benchmark"]["faithfulness_pct"] == 100.0
