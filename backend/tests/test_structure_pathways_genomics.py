"""
Unit tests for Modules 4, 5, 6:
PDB, CATH/SCOP, mutation mapping, PROSITE regex mining, KEGG, STRING, Ensembl/UCSC, and BioAggregator.
"""
from __future__ import annotations

import pytest
import respx
from fastapi.testclient import TestClient

from backend.api.bio_schemas import StructureRecord
from backend.main import app
from backend.utils.bio_aggregator import BioAggregator
from backend.utils.functional_client import FunctionalClient, prosite_to_regex
from backend.utils.genomics_client import GenomicsClient
from backend.utils.pdb_client import PDBClient

MOCK_PDB_ENTRY = {
    "struct": {"title": "Crystal structure of ancestral woolly mammoth hemoglobin"},
    "rcsb_entry_info": {
        "resolution_combined": [1.55],
        "polymer_entity_count_protein": 1,
        "nonpolymer_bound_components": ["HEM", "OXY"],
    },
    "exptl": [{"method": "X-RAY DIFFRACTION"}],
    "rcsb_accession_info": {"deposit_date": "2010-05-12T00:00:00Z"},
}

MOCK_STRING_RESPONSE = [
    {
        "stringId_A": "9606.ENSP00000335255",
        "stringId_B": "9606.ENSP00000252519",
        "preferredName_A": "FOXP2",
        "preferredName_B": "CNTNAP2",
        "score": 0.895,
        "escore": 0.65,
        "dscore": 0.5,
        "ascore": 0.4,
        "tscore": 0.7,
        "nscore": 0.0,
    }
]

MOCK_KEGG_RESPONSE = """ENTRY       map05100                  Pathway
NAME        Bacterial invasion of epithelial cells
DESCRIPTION Pathogenic bacteria can induce cellular changes...
"""

MAMMOTH_PROTEIN_SEQ = (
    "MVHLTPEEKSAVTALWGKVNVDEVGGEALGRLLVVYPWTQRFFESFGDLSTPDAVMGNPK"
    "VKAHGKKVLGAFSDGLAHLDNLKGTFATLSELHCDKLHVDPENFRLLGNVLVCVLAHHFG"
    "KEFTPPVQAAYQKVVAGVANALAHKYH"
)


def test_prosite_to_regex_conversion():
    # Globin pattern: [LIVMF]-x-H-[LIVMFY]
    regex = prosite_to_regex("[LIVMF]-x-H-[LIVMFY]")
    assert regex == "[LIVMF][A-Z]H[LIVMFY]"

    # Test excluded set {AM}
    regex_excluded = prosite_to_regex("A-{AM}-C")
    assert regex_excluded == "A[^AM]C"


def test_scan_prosite_motifs():
    func = FunctionalClient()
    hits = func.scan_prosite_motifs(MAMMOTH_PROTEIN_SEQ)
    # Mammoth hemoglobin should match Globin signature PS01033
    globin_hits = [h for h in hits if h.id == "PS01033"]
    assert len(globin_hits) >= 1
    hit = globin_hits[0]
    assert hit.database == "PROSITE"
    assert hit.start > 0


@respx.mock
def test_pdb_client_get_structure():
    respx.get("https://data.rcsb.org/rest/v1/core/entry/3VRF").respond(
        status_code=200, json=MOCK_PDB_ENTRY
    )
    respx.get("https://data.rcsb.org/rest/v1/core/polymer_entity/3VRF/1").respond(
        status_code=200,
        json={"rcsb_polymer_entity_container_identifiers": {"auth_asym_ids": ["A", "B"]}},
    )
    respx.get("https://www.ebi.ac.uk/pdbe/api/mappings/cath/3vrf").respond(
        status_code=200,
        json={"3vrf": {"CATH": {"1.10.490.10": {"homology": "Globins"}}}},
    )
    respx.get("https://www.ebi.ac.uk/pdbe/api/mappings/scop/3vrf").respond(
        status_code=200,
        json={"3vrf": {"SCOP": {"12345": {"fold": "Globin-like"}}}},
    )

    client = PDBClient()
    struct = client.get_structure("3VRF")
    assert isinstance(struct, StructureRecord)
    assert struct.pdb_id == "3VRF"
    assert struct.resolution_angstrom == 1.55
    assert struct.cath_codes == ["1.10.490.10"]
    assert struct.cath_names == ["Globins"]
    assert struct.scop_folds == ["Globin-like"]
    assert "HEM" in struct.ligands
    assert "A" in struct.chains


def test_pdb_mutation_mapping():
    client = PDBClient()
    muts = [
        {"ancestral": "T", "position": 12, "derived": "A", "label": "T12A"},
        {"ancestral": "A", "position": 86, "derived": "S", "label": "A86S"},
        {"ancestral": "E", "position": 101, "derived": "Q", "label": "E101Q"},
    ]
    mapped = client.map_mutations_to_structure("3VRF", muts, chain="B")
    assert len(mapped) == 3
    assert mapped[0]["residue_number"] == 12
    assert mapped[0]["label"] == "T12A"
    assert mapped[0]["color"] == "#ef4444"


@respx.mock
def test_functional_client_string_and_kegg():
    respx.get("https://string-db.org/api/json/network").respond(
        status_code=200, json=MOCK_STRING_RESPONSE
    )
    respx.get("https://rest.kegg.jp/get/map05100").respond(
        status_code=200, text=MOCK_KEGG_RESPONSE
    )

    client = FunctionalClient()

    # STRING
    edges = client.get_string_interactions("FOXP2")
    assert len(edges) == 1
    assert edges[0].source == "FOXP2"
    assert edges[0].target == "CNTNAP2"
    assert edges[0].score == 0.895

    # KEGG
    kegg_hit = client.get_kegg_pathway("map05100")
    assert kegg_hit is not None
    assert kegg_hit.pathway_id == "map05100"
    assert "Bacterial invasion" in kegg_hit.name


def test_genomics_client_locus_and_ucsc_links():
    client = GenomicsClient()
    locus = client.get_gene_locus("FOXP2")
    assert locus is not None
    assert locus.chromosome == "chr7"
    assert "genome.ucsc.edu" in locus.ucsc_url
    assert "neandAltai=pack" in locus.ucsc_url

    geo_url = client.format_geo_link("GSE123456")
    assert "ncbi.nlm.nih.gov/geo" in geo_url


@respx.mock
def test_unified_bio_lookup_mammoth():
    respx.get("https://rest.uniprot.org/uniprotkb/D3U1H9.json").respond(
        status_code=200,
        json={
            "primaryAccession": "D3U1H9",
            "uniProtkbId": "D3U1H9_MAMPR",
            "proteinDescription": {"recommendedName": {"fullName": {"value": "Hemoglobin subunit beta"}}},
            "organism": {"scientificName": "Mammuthus primigenius", "taxonId": 37349},
            "sequence": {"value": MAMMOTH_PROTEIN_SEQ, "length": len(MAMMOTH_PROTEIN_SEQ)},
            "features": [],
            "uniProtKBCrossReferences": [],
        },
    )
    respx.get("https://string-db.org/api/json/network").respond(status_code=200, json=[])
    respx.get("https://rest.kegg.jp/get/map05100").respond(status_code=200, text=MOCK_KEGG_RESPONSE)

    agg = BioAggregator()
    res = agg.lookup("Mammoth")
    assert res.organism == "Mammuthus primigenius"
    assert res.protein_record is not None
    assert res.protein_record.accession == "D3U1H9"
    # Should have scanned PROSITE Globin domain
    assert any(d.id == "PS01033" for d in res.domains)


@respx.mock
def test_api_structure_and_pathway_routes():
    respx.get("https://data.rcsb.org/rest/v1/core/entry/3VRF").respond(
        status_code=200, json=MOCK_PDB_ENTRY
    )
    respx.get("https://string-db.org/api/json/network").respond(
        status_code=200, json=MOCK_STRING_RESPONSE
    )
    respx.get("https://rest.kegg.jp/get/map05100").respond(
        status_code=200, text=MOCK_KEGG_RESPONSE
    )

    client = TestClient(app)

    # Structure
    r1 = client.get("/api/bio/structure/3VRF")
    assert r1.status_code == 200
    assert r1.json()["pdb_id"] == "3VRF"

    # Motif scan
    r2 = client.post("/api/bio/motifs/scan", params={"sequence": MAMMOTH_PROTEIN_SEQ})
    assert r2.status_code == 200
    assert r2.json()["count"] >= 1

    # Interactions
    r3 = client.get("/api/bio/interactions/FOXP2")
    assert r3.status_code == 200
    assert r3.json()["count"] == 1

    # Locus
    r4 = client.get("/api/bio/locus/FOXP2")
    assert r4.status_code == 200
    assert r4.json()["chromosome"] == "chr7"
