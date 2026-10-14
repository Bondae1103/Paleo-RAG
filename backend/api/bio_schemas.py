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
    gene_symbols: list[str] = Field(default_factory=list)
    entry_type: Optional[str] = None
    reviewed: bool = False
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
    uniprot_validation: Optional[dict[str, Any]] = None


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


class UniprotValidationAnnotation(BaseModel):
    """Provenance for a target/extant *_uniprot_acc value, from a live UniProt audit."""
    status: str  # verified_exact | verified_proxy | corrected | unverified
    checked_organism: Optional[str] = None
    checked_taxon_id: Optional[int] = None
    checked_gene_symbols: list[str] = Field(default_factory=list)
    evidence_source: str = "https://rest.uniprot.org/uniprotkb/"
    validated_at: Optional[str] = None
    previous_accession: Optional[str] = None
    note: Optional[str] = None


class NcbiValidationAnnotation(BaseModel):
    """Provenance for a *_nucleotide_acc value, from a live NCBI E-utilities audit."""
    status: str  # verified_exact | verified_proxy | unverified
    checked_organism: Optional[str] = None
    checked_taxid: Optional[int] = None
    evidence_source: Optional[str] = None
    validated_at: Optional[str] = None
    previous_accession: Optional[str] = None
    note: Optional[str] = None


class EnsemblValidationAnnotation(BaseModel):
    """Provenance for a genomics locus, from a live Ensembl REST audit."""
    status: str  # verified_live | unverified
    evidence_source: Optional[str] = None
    validated_at: Optional[str] = None
    note: Optional[str] = None


class KeggValidationAnnotation(BaseModel):
    """Provenance for a pathway.kegg_id value, from a live KEGG REST audit."""
    status: str  # verified_live | corrected | unverified
    evidence_source: Optional[str] = None
    validated_at: Optional[str] = None
    previous_kegg_id: Optional[str] = None
    note: Optional[str] = None


class LocusAnnotation(BaseModel):
    gene_symbol: str
    protein_name: str
    # None when no live NCBI Nucleotide record verifiably represents this
    # organism/gene; see extinct_nucleotide_validation for why.
    extinct_nucleotide_acc: Optional[str] = None
    extinct_uniprot_acc: Optional[str] = None
    extinct_sequence_dna: str
    extinct_sequence_aa: str
    extinct_uniprot_validation: Optional[UniprotValidationAnnotation] = None
    extinct_nucleotide_validation: Optional[NcbiValidationAnnotation] = None


class ExtantCounterpartAnnotation(BaseModel):
    common_name: str
    scientific_name: str
    # None when no live NCBI Nucleotide record verifiably represents this
    # organism/gene; see extant_nucleotide_validation for why.
    extant_nucleotide_acc: Optional[str] = None
    extant_uniprot_acc: Optional[str] = None
    extant_sequence_dna: str
    extant_sequence_aa: str
    extant_uniprot_validation: Optional[UniprotValidationAnnotation] = None
    extant_nucleotide_validation: Optional[NcbiValidationAnnotation] = None


class GenomicsAnnotation(BaseModel):
    # None when no live-verified Ensembl gene record exists for the organism
    # this locus claims; see ensembl_validation for why.
    chromosome: Optional[str] = None
    start: Optional[int] = None
    end: Optional[int] = None
    assembly: Optional[str] = None
    ensembl_species: Optional[str] = None
    ensembl_gene_id: Optional[str] = None
    ensembl_validation: Optional[EnsemblValidationAnnotation] = None


class PathwayAnnotation(BaseModel):
    # None when no live-confirmed KEGG pathway membership exists for this
    # gene; see kegg_validation for why.
    kegg_id: Optional[str] = None
    pathway_name: str
    kegg_validation: Optional[KeggValidationAnnotation] = None


class FossilRecordAnnotation(BaseModel):
    pbdb_taxon_id: Optional[str] = None
    pbdb_taxon_name: Optional[str] = None
    # None when this taxon has no PaleoBioDB record at all (e.g. bacteria,
    # viruses); otherwise the taxon-specific classic/checkTaxonInfo record
    # page, not the Navigator app's generic homepage.
    pbdb_navigator_url: Optional[str] = None
    pbdb_api_url: Optional[str] = None
    fossil_occurrences_count: Optional[int] = 0
    first_appearance_ma: Optional[float] = None
    last_appearance_ma: Optional[float] = None
    geological_interval: str = "Pleistocene"


class MolecularSampleAnnotation(BaseModel):
    sample_id: str
    gene_symbol: str
    protein_name: str
    category: str
    biological_significance: str
    extinct_uniprot_acc: Optional[str] = None
    extinct_nucleotide_acc: Optional[str] = None
    extinct_sequence_aa: str
    extinct_uniprot_validation: Optional[UniprotValidationAnnotation] = None
    extinct_nucleotide_validation: Optional[NcbiValidationAnnotation] = None
    extant_counterpart: ExtantCounterpartAnnotation
    structure: StructureAnnotation
    genomics: GenomicsAnnotation
    pathway: PathwayAnnotation


class TaxonRegistryEntry(BaseModel):
    tax_id: str
    common_name: str
    scientific_name: str
    clade: str
    epoch: str
    extinction_date: str
    key_trait: str
    description: str
    image_url: Optional[str] = None
    image_caption: Optional[str] = None
    habitat_range: Optional[str] = None
    geological_range: Optional[str] = None
    diet_ecology: Optional[str] = None
    morphology: Optional[str] = None
    extinction_driver: Optional[str] = None
    target_locus: LocusAnnotation
    extant_counterpart: ExtantCounterpartAnnotation
    structure: StructureAnnotation
    genomics: GenomicsAnnotation
    pathway: PathwayAnnotation
    molecular_samples: Optional[list[MolecularSampleAnnotation]] = None
    fossil_record: Optional[FossilRecordAnnotation] = None
    publications: Optional[list[dict]] = None
    pbdb: Optional[dict] = None
    included_species: Optional[list[str]] = None
    scope_note: Optional[str] = None


class AtlasListResponse(BaseModel):
    total_taxa: int
    taxa: list[TaxonRegistryEntry]
    catalog: list[TaxonRegistryEntry] = Field(default_factory=list)
