"""
Unit tests for Module 3: NCBI E-utilities, UniProtKB, and ENA/DDBJ clients.
"""
from __future__ import annotations

import pytest
import respx
from fastapi.testclient import TestClient

from backend.api.bio_schemas import ProteinRecord, SequenceRecord
from backend.main import app
from backend.utils.ena_ddbj_client import EnaDdbjClient
from backend.utils.error_types import DatabaseNotFoundError
from backend.utils.http_client import BioHttpClient
from backend.utils.ncbi_client import NCBIClient
from backend.utils.uniprot_client import UniProtClient

MOCK_GB_MAMMOTH = """LOCUS       HQ184444                 444 bp    DNA     linear   MAM 14-MAY-2010
DEFINITION  Mammuthus primigenius hemoglobin subunit beta (HBB) gene.
ACCESSION   HQ184444
VERSION     HQ184444.1
SOURCE      Mammuthus primigenius
  ORGANISM  Mammuthus primigenius
FEATURES             Location/Qualifiers
     source          1..444
                     /organism="Mammuthus primigenius"
     gene            1..444
                     /gene="HBB"
ORIGIN      
        1 atggtgcacc tgactcctga ggagaagtct gccgttactg ccctgtgggg caaggtgaac
       61 gtggatgaag ttggtggtga ggccctgggc aggctgctgg ttgtctaccc ctggacccag
      121 aggttctttg agtcctttgg ggatctgtcc actcctgatg ctgttatggg caaccctaag
      181 gtgaaggctc atggcaagaa agtgctcggt gcctttagtg atggcctggc tcacctggac
      241 aacctcaagg gcacctttgc cacactgagt gagctgcact gtgacaagct gcacgtggat
      301 cctgagaact tcaggctcct gggcaacgtg ctggtctgtg tgctggccca tcactttggc
      361 aaagaattca ctccaccagt gcaggctgcc tatcagaaag tggtggctgg tgtggctaat
      421 gccctggccc acaagtatca ctaa
//
"""

MOCK_UNIPROT_D3U1H9 = {
    "primaryAccession": "D3U1H9",
    "uniProtkbId": "D3U1H9_MAMPR",
    "proteinDescription": {
        "recommendedName": {"fullName": {"value": "Hemoglobin subunit beta"}}
    },
    "organism": {
        "scientificName": "Mammuthus primigenius",
        "taxonId": 37349,
    },
    "sequence": {
        "value": "MVHLTPEEKSAVTALWGKVNVDEVGGEALGRLLVVYPWTQRFFESFGDLSTPDAVMGNPKVKAHGKKVLGAFSDGLAHLDNLKGTFATLSELHCDKLHVDPENFRLLGNVLVCVLAHHFGKEFTPPVQAAYQKVVAGVANALAHKYH",
        "length": 147,
    },
    "features": [
        {"type": "Binding site", "location": {"start": {"value": 93}, "end": {"value": 93}}, "description": "Heme (iron axial ligand)"},
        {"type": "Disulfide bond", "location": {"start": {"value": 94}, "end": {"value": 113}}, "description": "Intra-chain"},
        {"type": "Modified residue", "location": {"start": {"value": 2}, "end": {"value": 2}}, "description": "N-acetylvaline"},
    ],
    "uniProtKBCrossReferences": [
        {"database": "PIR", "id": "PIR00123", "properties": []},
        {"database": "PDB", "id": "3VRF", "properties": [{"key": "Method", "value": "X-ray"}]},
        {"database": "Pfam", "id": "PF00042", "properties": [{"key": "EntryName", "value": "Globin"}]},
        {"database": "PROSITE", "id": "PS01033", "properties": [{"key": "EntryName", "value": "GLOBIN"}]},
        {"database": "GO", "id": "GO:0005344", "properties": [{"key": "GoTerm", "value": "F:oxygen carrier activity"}]},
    ],
}


@respx.mock
def test_ncbi_client_fetch_record():
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").respond(
        status_code=200, text=MOCK_GB_MAMMOTH
    )

    client = NCBIClient()
    rec = client.get_sequence_record("HQ184444.1")
    assert isinstance(rec, SequenceRecord)
    assert rec.id == "HQ184444.1"
    assert rec.length == 444
    assert len(rec.features) >= 2


@respx.mock
def test_ncbi_client_search():
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi").respond(
        status_code=200,
        json={"esearchresult": {"idlist": ["12345", "67890"]}},
    )

    client = NCBIClient()
    ids = client.search_nucleotide("Mammuthus primigenius HBB")
    assert ids == ["12345", "67890"]


@respx.mock
def test_uniprot_client_get_protein():
    respx.get("https://rest.uniprot.org/uniprotkb/D3U1H9.json").respond(
        status_code=200, json=MOCK_UNIPROT_D3U1H9
    )

    client = UniProtClient()
    prot = client.get_protein("D3U1H9")
    assert isinstance(prot, ProteinRecord)
    assert prot.accession == "D3U1H9"
    assert prot.protein_name == "Hemoglobin subunit beta"
    assert prot.organism == "Mammuthus primigenius"
    assert len(prot.active_sites) == 1
    assert len(prot.disulfide_bonds) == 1
    assert len(prot.ptms) == 1
    assert prot.pir_ids == ["PIR00123"]
    assert "PDB" in prot.cross_references
    assert "Pfam" in prot.cross_references


@respx.mock
def test_uniprot_client_not_found():
    respx.get("https://rest.uniprot.org/uniprotkb/NONEXISTENT.json").respond(status_code=404)
    client = UniProtClient()
    with pytest.raises(DatabaseNotFoundError):
        client.get_protein("NONEXISTENT")


@respx.mock
def test_ena_client_fasta_and_filereport():
    respx.get("https://www.ebi.ac.uk/ena/browser/api/fasta/HQ184444").respond(
        status_code=200, text=">ENA|HQ184444|HQ184444.1 Mammuthus\nATGGTCGATC\n"
    )
    respx.get("https://www.ebi.ac.uk/ena/portal/api/filereport").respond(
        status_code=200,
        text="run_accession\tscientific_name\nERR123456\tMammuthus primigenius\n",
    )

    client = EnaDdbjClient()
    rec = client.get_sequence_record("HQ184444")
    assert rec.id == "HQ184444"
    assert rec.length == 10

    report = client.get_filereport("PRJEB12345")
    assert len(report) == 1
    assert report[0]["run_accession"] == "ERR123456"


@respx.mock
def test_api_molecular_endpoints():
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").respond(
        status_code=200, text=MOCK_GB_MAMMOTH
    )
    respx.get("https://rest.uniprot.org/uniprotkb/D3U1H9.json").respond(
        status_code=200, json=MOCK_UNIPROT_D3U1H9
    )

    test_client = TestClient(app)

    # NCBI endpoint
    r1 = test_client.get("/api/bio/nucleotide/HQ184444.1")
    assert r1.status_code == 200
    assert r1.json()["id"] == "HQ184444.1"

    # UniProt endpoint
    r2 = test_client.get("/api/bio/protein/D3U1H9")
    assert r2.status_code == 200
    assert r2.json()["accession"] == "D3U1H9"
    assert r2.json()["pir_ids"] == ["PIR00123"]
