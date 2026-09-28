"""
Unit tests for Module 1 Sequence Workbench:
Validation, FASTA/GenBank/EMBL conversion, Central Dogma, 6-frame ORF finder, and submission checking.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.api.bio_schemas import (
    ConversionRequest,
    SequenceFormat,
    SequenceType,
    SubmissionValidationRequest,
    TranslationRequest,
)
from backend.main import app
from backend.utils.sequence_tools import (
    convert_sequence_format,
    detect_sequence_type,
    run_central_dogma,
    validate_sequence,
    validate_submission_metadata,
)

# Reference: Woolly Mammoth HBB partial coding sequence
MAMMOTH_HBB_DNA = (
    "ATGGTGCACCTGACTCCTGAGGAGAAGTCTGCCGTTACTGCCCTGTGGGGCAAGGTG"
    "AACGTGGATGAAGTTGGTGGTGAGGCCCTGGGCAGGCTGCTGGTTGTCTACCCCTGG"
    "ACCCAGAGGTTCTTTGAGTCCTTTGGGGATCTGTCCACTCCTGATGCTGTTATGGGC"
    "AACCCTAAGGTGAAGGCTCATGGCAAGAAAGTGCTCGGTGCCTTTAGTGATGGCCTG"
    "GCTCACCTGGACAACCTCAAGGGCACCTTTGCCACACTGAGTGAGCTGCACTGTGAC"
    "AAGCTGCACGTGGATCCTGAGAACTTCAGGCTCCTGGGCAACGTGCTGGTCTGTGTG"
    "CTGGCCCATCACTTTGGCAAAGAATTCACTCCACCAGTGCAGGCTGCCTATCAGAAA"
    "GTGGTGGCTGGTGTGGCTAATGCCCTGGCCCACAAGTATCACTAA"
)

FASTA_SAMPLE = f""">HQ184444.1 Mammuthus primigenius hemoglobin subunit beta
{MAMMOTH_HBB_DNA}
"""

GENBANK_SAMPLE = f"""LOCUS       HQ184444                 444 bp    DNA     linear   MAM 14-MAY-2010
DEFINITION  Mammuthus primigenius hemoglobin subunit beta (HBB) gene.
ACCESSION   HQ184444
VERSION     HQ184444.1
SOURCE      Mammuthus primigenius (woolly mammoth)
  ORGANISM  Mammuthus primigenius
FEATURES             Location/Qualifiers
     source          1..444
                     /organism="Mammuthus primigenius"
     CDS             1..444
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


def test_detect_sequence_type():
    assert detect_sequence_type("ATGCGATCGAT") == SequenceType.dna
    assert detect_sequence_type("AUGCGAUCGAU") == SequenceType.rna
    assert detect_sequence_type("MVHLTPEEKSAVTALWGKVN") == SequenceType.protein
    assert detect_sequence_type("12345!@#$") == SequenceType.unknown


def test_validate_sequence_dna_clean():
    res = validate_sequence("ATGCgtacNNN")
    assert res.is_valid is True
    assert res.seq_type == SequenceType.dna
    assert res.length == 11
    assert res.gc_percent == 36.36
    assert res.ambiguity_index > 0  # has NNN
    assert len(res.invalid_characters) == 0


def test_validate_sequence_invalid_characters():
    res = validate_sequence("ATGCP1234")
    assert res.is_valid is False
    assert "P" in res.invalid_characters or "1" in res.invalid_characters


def test_validate_sequence_empty():
    res = validate_sequence("")
    assert res.is_valid is False
    assert res.length == 0


def test_convert_fasta_to_genbank():
    out_text, records = convert_sequence_format(FASTA_SAMPLE, SequenceFormat.fasta, SequenceFormat.genbank)
    assert "LOCUS" in out_text
    assert "ORIGIN" in out_text
    assert len(records) == 1
    assert records[0].id == "HQ184444.1"
    assert records[0].length == len(MAMMOTH_HBB_DNA)
    assert records[0].seq_type == SequenceType.dna


def test_convert_genbank_to_fasta():
    out_text, records = convert_sequence_format(GENBANK_SAMPLE, SequenceFormat.genbank, SequenceFormat.fasta)
    assert out_text.startswith(">HQ184444.1")
    assert len(records) == 1
    assert records[0].name == "HQ184444"
    assert len(records[0].features) >= 1


def test_convert_raw_sequence():
    raw = "atggtgcacctgactcctgaggagaagtctgccgttactgccctgtgg"
    out_text, records = convert_sequence_format(raw, SequenceFormat.fasta, SequenceFormat.fasta)
    assert out_text.startswith(">PaleoSeq_1")
    assert records[0].length == len(raw)


def test_central_dogma_transcription_and_orfs():
    res = run_central_dogma(MAMMOTH_HBB_DNA, min_orf_length_aa=30)
    assert "U" in res.rna_sequence
    assert "T" not in res.rna_sequence
    assert len(res.frames) == 6

    # Frame +1 should have the complete Mammoth HBB coding translation
    frame1 = next(f for f in res.frames if f.frame == 1)
    assert frame1.translation.startswith("MVHLTPEEKSAVTALWGKV")
    assert frame1.translation.endswith("*")

    # Longest ORF should be detected
    assert res.longest_orf is not None
    assert res.longest_orf.length_aa >= 140
    assert res.longest_orf.strand == 1
    assert res.longest_orf.start == 0


def test_submission_metadata_validator():
    req = SubmissionValidationRequest(
        locus_name="MAMP_HBB",
        sequence=MAMMOTH_HBB_DNA,
        molecule_type="DNA",
        organism="Mammuthus primigenius",
        definition="Woolly mammoth hemoglobin beta chain",
        authors=["Yuan, H.", "Campbell, K.L."],
    )
    res = validate_submission_metadata(req)
    assert res.is_valid is True
    assert len(res.errors) == 0
    assert res.preview_genbank_record is not None
    assert "MAMP_HBB" in res.preview_genbank_record


def test_submission_metadata_validator_short_sequence():
    req = SubmissionValidationRequest(
        locus_name="SHORT",
        sequence="ATGCATGC",  # < 50 bp
        organism="Mammuthus primigenius",
        definition="Too short",
    )
    res = validate_submission_metadata(req)
    assert res.is_valid is False
    assert any("minimum required" in e for e in res.errors)


def test_api_sequence_endpoints():
    client = TestClient(app)

    # Validate
    resp = client.post("/api/bio/sequence/validate", params={"sequence": MAMMOTH_HBB_DNA[:60]})
    assert resp.status_code == 200
    assert resp.json()["is_valid"] is True
    assert resp.json()["length"] == 60

    # Convert
    conv_req = ConversionRequest(
        input_text=FASTA_SAMPLE,
        input_format=SequenceFormat.fasta,
        output_format=SequenceFormat.genbank,
    )
    resp = client.post("/api/bio/sequence/convert", json=conv_req.model_dump())
    assert resp.status_code == 200
    assert "LOCUS" in resp.json()["output_text"]

    # Dogma
    dogma_req = TranslationRequest(sequence=MAMMOTH_HBB_DNA[:120], min_orf_length_aa=10)
    resp = client.post("/api/bio/sequence/dogma", json=dogma_req.model_dump())
    assert resp.status_code == 200
    assert "rna_sequence" in resp.json()
    assert len(resp.json()["frames"]) == 6
