"""
Sequence Workbench utility: IUPAC validation, metrics, format conversions (Bio.SeqIO),
Central Dogma transcription/translation, 6-frame ORF finder, and submission validator.
"""
from __future__ import annotations

import io
import re
from typing import Any, Optional

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from backend.api.bio_schemas import (
    OpenReadingFrame,
    SequenceFeature,
    SequenceFormat,
    SequenceRecord as SchemaSeqRecord,
    SequenceType,
    SubmissionValidationRequest,
    SubmissionValidationResponse,
    TranslationFrame,
    TranslationResponse,
    ValidationResult,
)
from backend.utils.error_types import SequenceConversionError, SequenceValidationError

# IUPAC character sets
DNA_STRICT = set("ACGT")
DNA_AMBIGUOUS = set("ACGTMRWSYKVHDBXN")
RNA_STRICT = set("ACGU")
RNA_AMBIGUOUS = set("ACGUMRWSYKVHDBXN")
PROTEIN_CHARS = set("ACDEFGHIKLMNPQRSTVWYBZX*")

STOP_CODONS_DNA = {"TAA", "TAG", "TGA"}
START_CODONS_DNA = {"ATG"}


def detect_sequence_type(raw_seq: str) -> SequenceType:
    # Remove fasta headers if present
    lines = raw_seq.strip().splitlines()
    body = "".join(line.strip() for line in lines if not line.strip().startswith(">"))
    clean = re.sub(r"\s+", "", body).upper()
    if not clean:
        return SequenceType.unknown

    chars = set(clean)
    if chars.issubset(RNA_AMBIGUOUS) and "U" in chars and "T" not in chars:
        return SequenceType.rna
    if chars.issubset(DNA_AMBIGUOUS):
        return SequenceType.dna
    if chars.issubset(PROTEIN_CHARS):
        return SequenceType.protein
    return SequenceType.unknown


def validate_sequence(raw_seq: str, expected_type: Optional[SequenceType] = None) -> ValidationResult:
    # Remove fasta headers if present
    lines = raw_seq.strip().splitlines()
    body = "".join(line.strip() for line in lines if not line.strip().startswith(">"))
    clean = re.sub(r"\s+", "", body).upper()
    if not clean:
        return ValidationResult(
            is_valid=False,
            seq_type=SequenceType.unknown,
            length=0,
            gc_percent=0.0,
            molecular_weight_kda=0.0,
            ambiguity_index=0.0,
            details="Sequence is empty.",
        )

    detected = detect_sequence_type(clean)
    target_type = expected_type if (expected_type and expected_type != SequenceType.unknown) else detected

    invalid_chars = []
    if target_type == SequenceType.dna:
        allowed = DNA_AMBIGUOUS.union({"-", "*"})
    elif target_type == SequenceType.rna:
        allowed = RNA_AMBIGUOUS.union({"-", "*"})
    elif target_type == SequenceType.protein:
        allowed = PROTEIN_CHARS.union({"-", "*"})
    else:
        allowed = DNA_AMBIGUOUS.union(PROTEIN_CHARS).union({"-", "*"})

    for ch in sorted(set(clean)):
        if ch not in allowed:
            invalid_chars.append(ch)

    is_valid = len(invalid_chars) == 0 and target_type != SequenceType.unknown
    length = len(clean)

    # Compute GC%
    if target_type in (SequenceType.dna, SequenceType.rna):
        g_count = clean.count("G")
        c_count = clean.count("C")
        gc_percent = round(((g_count + c_count) / length) * 100.0, 2) if length > 0 else 0.0
        # Ambiguity index: proportion of non-ACGT/U characters
        strict_set = DNA_STRICT if target_type == SequenceType.dna else RNA_STRICT
        ambig_count = sum(1 for ch in clean if ch not in strict_set)
        ambiguity_index = round(ambig_count / length, 4) if length > 0 else 0.0
        # Molecular weight estimation (~330 Da per nt)
        molecular_weight_kda = round((length * 330.0) / 1000.0, 3)
    else:
        gc_percent = 0.0
        ambig_count = sum(1 for ch in clean if ch in ("B", "Z", "X", "*"))
        ambiguity_index = round(ambig_count / length, 4) if length > 0 else 0.0
        # Average amino acid weight ~110 Da
        molecular_weight_kda = round((length * 110.0) / 1000.0, 3)

    details = (
        f"Valid {target_type.value.upper()} sequence ({length} bp/aa)."
        if is_valid
        else f"Invalid characters found: {', '.join(invalid_chars)}"
    )

    return ValidationResult(
        is_valid=is_valid,
        seq_type=target_type,
        length=length,
        gc_percent=gc_percent,
        molecular_weight_kda=molecular_weight_kda,
        ambiguity_index=ambiguity_index,
        invalid_characters=invalid_chars,
        details=details,
    )


def convert_sequence_format(
    input_text: str,
    input_format: SequenceFormat,
    output_format: SequenceFormat,
) -> tuple[str, list[SchemaSeqRecord]]:
    """
    Convert sequences between FASTA, GenBank, and EMBL formats using Bio.SeqIO.
    Preserves or synthesizes required metadata (molecule_type, dates) so conversions
    are deterministic and standards-compliant.
    """
    clean_input = input_text.strip()
    if not clean_input:
        raise SequenceConversionError("Input sequence text cannot be empty.")

    # Detect if user pasted raw unformatted sequence instead of formal format
    is_raw = not clean_input.startswith(("> ", ">", "LOCUS", "ID   "))
    records: list[SeqRecord] = []

    if is_raw:
        seq_type = detect_sequence_type(clean_input)
        mol_type = "DNA" if seq_type == SequenceType.dna else ("RNA" if seq_type == SequenceType.rna else "protein")
        record = SeqRecord(
            Seq(re.sub(r"[\s\d\->]", "", clean_input).upper()),
            id="PaleoSeq_1",
            name="PaleoSeq_1",
            description="User-submitted sequence in PaleoRAG Sequence Workbench",
        )
        record.annotations["molecule_type"] = mol_type
        records.append(record)
    else:
        fmt_key = input_format.value
        try:
            in_stream = io.StringIO(clean_input)
            records = list(SeqIO.parse(in_stream, fmt_key))
        except Exception as exc:
            raise SequenceConversionError(f"Failed to parse input as {input_format.value}: {exc}")

    if not records:
        raise SequenceConversionError(f"No valid records found in input format '{input_format.value}'.")

    # Ensure required annotations are present for GenBank / EMBL export
    for i, rec in enumerate(records):
        if "molecule_type" not in rec.annotations:
            st = detect_sequence_type(str(rec.seq))
            rec.annotations["molecule_type"] = "DNA" if st == SequenceType.dna else ("RNA" if st == SequenceType.rna else "protein")
        if not rec.id or rec.id == "<unknown id>":
            rec.id = f"Seq_{i+1}"
        if not rec.name or rec.name == "<unknown name>":
            rec.name = rec.id[:16]

    out_stream = io.StringIO()
    out_fmt = output_format.value
    try:
        SeqIO.write(records, out_stream, out_fmt)
        output_text = out_stream.getvalue()
    except Exception as exc:
        raise SequenceConversionError(f"Failed to export records as {output_format.value}: {exc}")

    # Build normalized schema records
    schema_records: list[SchemaSeqRecord] = []
    for rec in records:
        s_val = str(rec.seq)
        st = detect_sequence_type(s_val)
        val = validate_sequence(s_val, expected_type=st)
        features: list[SequenceFeature] = []
        for feat in getattr(rec, "features", []):
            features.append(
                SequenceFeature(
                    type=feat.type,
                    location=str(feat.location),
                    qualifiers={k: v if isinstance(v, list) else [str(v)] for k, v in feat.qualifiers.items()},
                )
            )

        schema_records.append(
            SchemaSeqRecord(
                id=rec.id,
                name=rec.name,
                description=rec.description,
                sequence=s_val,
                length=len(s_val),
                seq_type=st,
                gc_content=val.gc_percent,
                molecular_weight_kda=val.molecular_weight_kda,
                ambiguity_index=val.ambiguity_index,
                features=features,
                annotations={k: str(v) for k, v in rec.annotations.items()},
            )
        )

    return output_text, schema_records


def run_central_dogma(dna_seq: str, min_orf_length_aa: int = 20) -> TranslationResponse:
    """
    Execute Central Dogma operations:
    1. DNA -> RNA transcription
    2. RNA -> cDNA reverse transcription
    3. DNA -> Reverse complement
    4. Six-frame translation (+1, +2, +3 forward, -1, -2, -3 reverse complement)
    5. Open Reading Frame (ORF) detection with start (ATG) and stop (TAA/TAG/TGA) codons
    """
    clean_dna = re.sub(r"[\s\d\->]", "", dna_seq).upper()
    if not clean_dna:
        raise SequenceValidationError("DNA sequence is empty.")

    seq_obj = Seq(clean_dna)
    rna_seq = str(seq_obj.transcribe())
    rev_comp = str(seq_obj.reverse_complement())

    frames: list[TranslationFrame] = []
    all_orfs: list[OpenReadingFrame] = []

    # Forward frames (+1, +2, +3)
    for shift in (0, 1, 2):
        frame_num = shift + 1
        sub_seq = clean_dna[shift:]
        # Truncate to multiple of 3
        usable_len = (len(sub_seq) // 3) * 3
        sub_seq_trim = sub_seq[:usable_len]
        trans = str(Seq(sub_seq_trim).translate()) if usable_len > 0 else ""
        orfs = find_orfs_in_strand(clean_dna, shift=shift, strand=+1, min_aa=min_orf_length_aa)
        frames.append(TranslationFrame(frame=frame_num, strand=+1, translation=trans, orfs=orfs))
        all_orfs.extend(orfs)

    # Reverse complement frames (-1, -2, -3)
    for shift in (0, 1, 2):
        frame_num = -(shift + 1)
        sub_seq = rev_comp[shift:]
        usable_len = (len(sub_seq) // 3) * 3
        sub_seq_trim = sub_seq[:usable_len]
        trans = str(Seq(sub_seq_trim).translate()) if usable_len > 0 else ""
        orfs = find_orfs_in_strand(rev_comp, shift=shift, strand=-1, min_aa=min_orf_length_aa, orig_len=len(clean_dna))
        frames.append(TranslationFrame(frame=frame_num, strand=-1, translation=trans, orfs=orfs))
        all_orfs.extend(orfs)

    longest_orf = max(all_orfs, key=lambda x: x.length_aa) if all_orfs else None

    return TranslationResponse(
        dna_sequence=clean_dna,
        rna_sequence=rna_seq,
        reverse_complement=rev_comp,
        frames=frames,
        longest_orf=longest_orf,
    )


def find_orfs_in_strand(
    seq_str: str,
    shift: int,
    strand: int,
    min_aa: int = 20,
    orig_len: Optional[int] = None,
) -> list[OpenReadingFrame]:
    """Find all open reading frames in a specific reading frame."""
    orfs: list[OpenReadingFrame] = []
    sub = seq_str[shift:]
    codons = [sub[i : i + 3] for i in range(0, len(sub) - 2, 3)]

    current_start: Optional[int] = None

    for idx, codon in enumerate(codons):
        if codon == "ATG" and current_start is None:
            current_start = idx
        elif codon in STOP_CODONS_DNA and current_start is not None:
            aa_len = idx - current_start
            if aa_len >= min_aa:
                orf_dna = "".join(codons[current_start:idx])
                protein = str(Seq(orf_dna).translate())
                # Calculate nucleotide coordinates
                rel_nt_start = shift + current_start * 3
                rel_nt_end = shift + idx * 3 + 3
                if strand == +1:
                    abs_start = rel_nt_start
                    abs_end = rel_nt_end
                else:
                    # Map reverse complement coordinates back to 5'->3' forward strand
                    assert orig_len is not None
                    abs_start = orig_len - rel_nt_end
                    abs_end = orig_len - rel_nt_start

                orfs.append(
                    OpenReadingFrame(
                        frame=strand * (shift + 1),
                        start=abs_start,
                        end=abs_end,
                        length_nt=len(orf_dna) + 3,
                        length_aa=aa_len,
                        strand=strand,
                        protein_sequence=protein,
                    )
                )
            current_start = None

    return orfs


def validate_submission_metadata(req: SubmissionValidationRequest) -> SubmissionValidationResponse:
    """Validate required fields for GenBank/EMBL-style sequence submissions."""
    errors: list[str] = []
    warnings: list[str] = []

    clean_seq = re.sub(r"[\s\d\->]", "", req.sequence).upper()
    if not clean_seq:
        errors.append("Sequence cannot be empty.")
    elif len(clean_seq) < 50:
        errors.append(f"Sequence length is {len(clean_seq)} bp; minimum required for database submission is 50 bp.")

    val = validate_sequence(clean_seq)
    if not val.is_valid:
        errors.append(f"Sequence contains invalid IUPAC characters: {', '.join(val.invalid_characters)}")

    if not req.locus_name or not req.locus_name.strip():
        errors.append("Locus name is required.")
    elif len(req.locus_name) > 16:
        warnings.append(f"Locus name '{req.locus_name}' exceeds recommended 16 characters.")

    if not req.organism or not req.organism.strip():
        errors.append("Organism scientific name is required (e.g., 'Mammuthus primigenius').")
    elif len(req.organism.split()) < 2 and not req.organism.lower().endswith("sp."):
        warnings.append(f"Organism name '{req.organism}' should be a scientific binomial (Genus species).")

    if not req.definition or not req.definition.strip():
        errors.append("Definition / Title line is required.")

    if not req.authors:
        warnings.append("No authors specified; submissions require submitting authors.")

    preview_gb: Optional[str] = None
    if not errors:
        rec = SeqRecord(
            Seq(clean_seq),
            id=req.locus_name,
            name=req.locus_name[:16],
            description=req.definition,
        )
        rec.annotations["molecule_type"] = req.molecule_type
        rec.annotations["topology"] = req.topology
        rec.annotations["organism"] = req.organism
        if req.authors:
            rec.annotations["references"] = [{"authors": ", ".join(req.authors), "title": req.title or req.definition}]

        out_s = io.StringIO()
        try:
            SeqIO.write([rec], out_s, "genbank")
            preview_gb = out_s.getvalue()
        except Exception as exc:
            warnings.append(f"Could not synthesize GenBank preview: {exc}")

    return SubmissionValidationResponse(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        preview_genbank_record=preview_gb,
    )
