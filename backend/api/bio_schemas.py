"""
Normalized Pydantic schemas for biological databases, sequence processing,
protein structures, and interaction networks.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class SequenceType(str, Enum):
    dna = "dna"
    rna = "rna"
    protein = "protein"
    unknown = "unknown"


class SequenceFormat(str, Enum):
    fasta = "fasta"
    genbank = "genbank"
    embl = "embl"


class SequenceFeature(BaseModel):
    type: str
    location: str
    qualifiers: dict[str, Any] = Field(default_factory=dict)


class SequenceRecord(BaseModel):
    id: str
    name: str
    description: str = ""
    sequence: str
    length: int
    seq_type: SequenceType = SequenceType.unknown
    gc_content: Optional[float] = None
    molecular_weight_kda: Optional[float] = None
    ambiguity_index: Optional[float] = None
    features: list[SequenceFeature] = Field(default_factory=list)
    annotations: dict[str, Any] = Field(default_factory=dict)


class ValidationRequest(BaseModel):
    sequence: str


class ValidationResult(BaseModel):
    is_valid: bool
    seq_type: SequenceType
    length: int
    gc_percent: float
    molecular_weight_kda: float
    ambiguity_index: float
    invalid_characters: list[str] = Field(default_factory=list)
    details: str = ""


class MotifScanRequest(BaseModel):
    sequence: str


class ConversionRequest(BaseModel):
    input_text: str
    input_format: SequenceFormat
    output_format: SequenceFormat


class ConversionResponse(BaseModel):
    output_text: str
    record_count: int
    records: list[SequenceRecord] = Field(default_factory=list)


class OpenReadingFrame(BaseModel):
    frame: int  # +1, +2, +3, -1, -2, -3
    start: int  # 0-indexed on input sequence
    end: int    # 0-indexed exclusive
    length_nt: int
    length_aa: int
    strand: int  # +1 or -1
    protein_sequence: str


class TranslationFrame(BaseModel):
    frame: int
    strand: int
    translation: str
    orfs: list[OpenReadingFrame] = Field(default_factory=list)


class TranslationRequest(BaseModel):
    sequence: str
    min_orf_length_aa: int = 20


class TranslationResponse(BaseModel):
    dna_sequence: str
    rna_sequence: str
    reverse_complement: str
    frames: list[TranslationFrame]
    longest_orf: Optional[OpenReadingFrame] = None


class SubmissionValidationRequest(BaseModel):
    locus_name: str
    sequence: str
    molecule_type: str = "DNA"
    topology: str = "linear"
    division: str = "INV"
    organism: str
    definition: str
    authors: list[str] = Field(default_factory=list)
    title: str = ""


class SubmissionValidationResponse(BaseModel):
    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    preview_genbank_record: Optional[str] = None


class ProteinRecord(BaseModel):
    accession: str
    entry_name: str
    protein_name: str
    organism: str
    organism_id: Optional[int] = None
    sequence: str
    length: int
    active_sites: list[dict[str, Any]] = Field(default_factory=list)
    disulfide_bonds: list[dict[str, Any]] = Field(default_factory=list)
    ptms: list[dict[str, Any]] = Field(default_factory=list)
    pir_ids: list[str] = Field(default_factory=list)
    cross_references: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)


class StructureRecord(BaseModel):
    pdb_id: str
    title: str
    resolution_angstrom: Optional[float] = None
    method: str = ""
    deposit_date: Optional[str] = None
    cath_codes: list[str] = Field(default_factory=list)
    cath_names: list[str] = Field(default_factory=list)
    scop_folds: list[str] = Field(default_factory=list)
    ligands: list[str] = Field(default_factory=list)
    chains: list[str] = Field(default_factory=list)
    coordinates_url: str = ""


class DomainHit(BaseModel):
    id: str
    database: str  # Pfam, PROSITE, InterPro
    name: str
    description: str = ""
    start: int
    end: int


class PathwayHit(BaseModel):
    pathway_id: str
    name: str
    database: str = "KEGG"
    url: str = ""
    description: Optional[str] = None


class InteractionEdge(BaseModel):
    source: str
    target: str
    score: float
    evidence_channels: dict[str, float] = Field(default_factory=dict)


class LocusLink(BaseModel):
    gene_symbol: str
    species: str
    chromosome: str
    start: int
    end: int
    assembly: str = "GRCh38"
    ensembl_url: str = ""
    ucsc_url: str = ""


class BioLookupResponse(BaseModel):
    query: str
    organism: Optional[str] = None
    nucleotide_record: Optional[SequenceRecord] = None
    protein_record: Optional[ProteinRecord] = None
    structure_record: Optional[StructureRecord] = None
    domains: list[DomainHit] = Field(default_factory=list)
    pathways: list[PathwayHit] = Field(default_factory=list)
    interactions: list[InteractionEdge] = Field(default_factory=list)
    locus: Optional[LocusLink] = None


class MutationAnnotation(BaseModel):
    position: int
    ancestral_aa: str
    derived_aa: str
    label: str
    grantham_distance: int = 0
    functional_impact: str = ""


class StructureAnnotation(BaseModel):
    pdb_id: str
    title: str
    resolution_angstrom: Optional[float] = None
    chain: str = "A"
    cath_code: str = ""
    scop_fold: str = ""
    mutations: list[MutationAnnotation] = Field(default_factory=list)


class LocusAnnotation(BaseModel):
    gene_symbol: str
    protein_name: str
    extinct_nucleotide_acc: str
    extinct_uniprot_acc: str
    extinct_sequence_dna: str
    extinct_sequence_aa: str


class ExtantCounterpartAnnotation(BaseModel):
    common_name: str
    scientific_name: str
    extant_nucleotide_acc: str
    extant_uniprot_acc: str
    extant_sequence_dna: str
    extant_sequence_aa: str


class GenomicsAnnotation(BaseModel):
    chromosome: str
    start: int
    end: int
    assembly: str
    ensembl_species: str


class PathwayAnnotation(BaseModel):
    kegg_id: str
    pathway_name: str


class TaxonRegistryEntry(BaseModel):
    tax_id: str
    common_name: str
    scientific_name: str
    clade: str
    epoch: str
    extinction_date: str
    key_trait: str
    description: str
    target_locus: LocusAnnotation
    extant_counterpart: ExtantCounterpartAnnotation
    structure: StructureAnnotation
    genomics: GenomicsAnnotation
    pathway: PathwayAnnotation


class AtlasListResponse(BaseModel):
    total_taxa: int
    taxa: list[TaxonRegistryEntry]
    catalog: list[TaxonRegistryEntry] = Field(default_factory=list)
