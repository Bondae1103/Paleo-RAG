"""
FastAPI router for biological databases, sequence processing, structures, and pathways.
"""
from __future__ import annotations

import logging
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.bio_schemas import (
    BioLookupResponse,
    ConversionRequest,
    ConversionResponse,
    InteractionEdge,
    LocusLink,
    PathwayHit,
    ProteinRecord,
    SequenceRecord,
    StructureRecord,
    SubmissionValidationRequest,
    SubmissionValidationResponse,
    TranslationRequest,
    TranslationResponse,
    ValidationResult,
)
from backend.config import Settings, get_settings
from backend.utils.http_client import BioHttpClient, get_bio_http_client

logger = logging.getLogger(__name__)

bio_router = APIRouter(prefix="/api/bio", tags=["Biological Databases & Sequence Tools"])


@bio_router.get("/health")
def bio_health(
    settings: Settings = Depends(get_settings),
    client: BioHttpClient = Depends(get_bio_http_client),
) -> dict[str, Any]:
    """Check connectivity and reachability of external biological database APIs."""
    services: dict[str, Any] = {}

    # Test NCBI E-utilities
    try:
        ncbi_resp = client.request(
            "GET",
            f"{settings.ncbi_eutils_base}/einfo.fcgi",
            params={"retmode": "json"},
            cache_ttl=3600,
        )
        services["ncbi"] = {"status": "ok" if ncbi_resp.status_code == 200 else "degraded", "code": ncbi_resp.status_code}
    except Exception as exc:
        services["ncbi"] = {"status": "unreachable", "error": str(exc)}

    # Test UniProt
    try:
        uniprot_resp = client.request(
            "GET",
            f"{settings.uniprot_api_base}/uniprotkb/P02100.json",
            cache_ttl=3600,
        )
        services["uniprot"] = {"status": "ok" if uniprot_resp.status_code == 200 else "degraded", "code": uniprot_resp.status_code}
    except Exception as exc:
        services["uniprot"] = {"status": "unreachable", "error": str(exc)}

    # Test RCSB PDB
    try:
        pdb_resp = client.request(
            "GET",
            f"{settings.rcsb_api_base}/core/entry/2A07",
            cache_ttl=3600,
        )
        services["rcsb_pdb"] = {"status": "ok" if pdb_resp.status_code == 200 else "degraded", "code": pdb_resp.status_code}
    except Exception as exc:
        services["rcsb_pdb"] = {"status": "unreachable", "error": str(exc)}

    # Test STRING
    try:
        string_resp = client.request(
            "GET",
            f"{settings.string_api_base}/json/version",
            cache_ttl=3600,
        )
        services["string"] = {"status": "ok" if string_resp.status_code == 200 else "degraded", "code": string_resp.status_code}
    except Exception as exc:
        services["string"] = {"status": "unreachable", "error": str(exc)}

    overall = "ok" if all(v.get("status") == "ok" for v in services.values()) else "degraded"
    return {
        "status": overall,
        "services": services,
        "cache_directory": settings.bio_cache_dir,
    }


# ==========================================
# MODULE 1: SEQUENCE WORKBENCH ENDPOINTS
# ==========================================

@bio_router.post("/sequence/validate", response_model=ValidationResult)
def api_validate_sequence(
    sequence: str = Query(..., description="Raw molecular sequence or FASTA/GenBank text"),
) -> ValidationResult:
    """Validate molecular sequence, detect type (DNA/RNA/Protein), check IUPAC, and compute metrics."""
    from backend.utils.sequence_tools import validate_sequence
    return validate_sequence(sequence)


@bio_router.post("/sequence/convert", response_model=ConversionResponse)
def api_convert_sequence(request: ConversionRequest) -> ConversionResponse:
    """Convert sequence records between FASTA, GenBank, and EMBL formats using Biopython SeqIO."""
    from backend.utils.error_types import SequenceConversionError
    from backend.utils.sequence_tools import convert_sequence_format

    try:
        out_text, records = convert_sequence_format(
            input_text=request.input_text,
            input_format=request.input_format,
            output_format=request.output_format,
        )
        return ConversionResponse(
            output_text=out_text,
            record_count=len(records),
            records=records,
        )
    except SequenceConversionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in sequence conversion")
        raise HTTPException(status_code=500, detail=f"Conversion error: {exc}")


@bio_router.post("/sequence/dogma", response_model=TranslationResponse)
def api_central_dogma(request: TranslationRequest) -> TranslationResponse:
    """Execute Central Dogma: transcription, reverse complement, 6-frame translation, and ORF detection."""
    from backend.utils.error_types import SequenceValidationError
    from backend.utils.sequence_tools import run_central_dogma

    try:
        return run_central_dogma(dna_seq=request.sequence, min_orf_length_aa=request.min_orf_length_aa)
    except SequenceValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in Central Dogma processing")
        raise HTTPException(status_code=500, detail=f"Central Dogma error: {exc}")


@bio_router.post("/sequence/submission-check", response_model=SubmissionValidationResponse)
def api_submission_check(request: SubmissionValidationRequest) -> SubmissionValidationResponse:
    """Validate sequence and submission metadata for GenBank/EMBL-style database submission."""
    from backend.utils.sequence_tools import validate_submission_metadata
    return validate_submission_metadata(request)


# ========================================================
# MODULE 3: NUCLEOTIDE & PROTEIN SEQUENCE DATABASES
# ========================================================

@bio_router.get("/nucleotide/{accession}", response_model=SequenceRecord)
def api_get_nucleotide(
    accession: str,
    client: BioHttpClient = Depends(get_bio_http_client),
    settings: Settings = Depends(get_settings),
) -> SequenceRecord:
    """Retrieve nucleotide record from NCBI GenBank or ENA/DDBJ and normalize."""
    from backend.utils.error_types import DatabaseNotFoundError
    from backend.utils.ncbi_client import NCBIClient
    from backend.utils.ena_ddbj_client import EnaDdbjClient

    ncbi = NCBIClient(settings=settings, http_client=client)
    try:
        return ncbi.get_sequence_record(accession)
    except DatabaseNotFoundError:
        # Fallback to ENA / INSDC
        try:
            ena = EnaDdbjClient(settings=settings, http_client=client)
            return ena.get_sequence_record(accession)
        except Exception:
            raise HTTPException(status_code=404, detail=f"Nucleotide accession '{accession}' not found in GenBank or ENA.")
    except Exception as exc:
        logger.exception(f"Error fetching nucleotide {accession}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve nucleotide record: {exc}")


@bio_router.get("/protein/{accession}", response_model=ProteinRecord)
def api_get_protein(
    accession: str,
    client: BioHttpClient = Depends(get_bio_http_client),
    settings: Settings = Depends(get_settings),
) -> ProteinRecord:
    """Retrieve curated protein record from UniProtKB (Swiss-Prot / TrEMBL)."""
    from backend.utils.error_types import DatabaseNotFoundError
    from backend.utils.uniprot_client import UniProtClient

    uniprot = UniProtClient(settings=settings, http_client=client)
    try:
        return uniprot.get_protein(accession)
    except DatabaseNotFoundError:
        raise HTTPException(status_code=404, detail=f"Protein accession '{accession}' not found in UniProtKB.")
    except Exception as exc:
        logger.exception(f"Error fetching protein {accession}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve protein record: {exc}")


@bio_router.get("/ena/{accession}")
def api_get_ena_report(
    accession: str,
    client: BioHttpClient = Depends(get_bio_http_client),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Retrieve ENA/DDBJ filereport metadata for an accession."""
    from backend.utils.ena_ddbj_client import EnaDdbjClient

    ena = EnaDdbjClient(settings=settings, http_client=client)
    report = ena.get_filereport(accession)
    return {"accession": accession, "report": report}


# ========================================================
# MODULE 4: PROTEIN STRUCTURE DATABASES (PDB, CATH, SCOP)
# ========================================================

@bio_router.get("/structure/{pdb_id}", response_model=StructureRecord)
def api_get_structure(
    pdb_id: str,
    client: BioHttpClient = Depends(get_bio_http_client),
    settings: Settings = Depends(get_settings),
) -> StructureRecord:
    """Retrieve 3D structure metadata, CATH codes, and SCOP folds from RCSB PDB and PDBe."""
    from backend.utils.error_types import DatabaseNotFoundError
    from backend.utils.pdb_client import PDBClient

    pdb = PDBClient(settings=settings, http_client=client)
    try:
        return pdb.get_structure(pdb_id)
    except DatabaseNotFoundError:
        raise HTTPException(status_code=404, detail=f"Structure '{pdb_id}' not found in RCSB PDB.")
    except Exception as exc:
        logger.exception(f"Error fetching structure {pdb_id}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve structure: {exc}")


@bio_router.get("/structure/{pdb_id}/coordinates")
def api_get_structure_coordinates(
    pdb_id: str,
    client: BioHttpClient = Depends(get_bio_http_client),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    """Download atomic coordinates in PDB format for web-based 3D molecular viewer."""
    from backend.utils.error_types import DatabaseNotFoundError
    from backend.utils.pdb_client import PDBClient

    pdb = PDBClient(settings=settings, http_client=client)
    try:
        text = pdb.fetch_coordinates_pdb(pdb_id)
        return {"pdb_id": pdb_id.upper(), "coordinates": text}
    except DatabaseNotFoundError:
        raise HTTPException(status_code=404, detail=f"Coordinates for '{pdb_id}' not found.")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve coordinates: {exc}")


@bio_router.post("/structure/{pdb_id}/mutations")
def api_map_mutations(
    pdb_id: str,
    mutations: list[dict[str, Any]],
    chain: str = "A",
    client: BioHttpClient = Depends(get_bio_http_client),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Map ancestral vs modern amino acid substitutions to PDB residue numbers for 3D highlighting."""
    from backend.utils.pdb_client import PDBClient

    pdb = PDBClient(settings=settings, http_client=client)
    mapped = pdb.map_mutations_to_structure(pdb_id=pdb_id, mutations=mutations, chain=chain)
    return {"pdb_id": pdb_id.upper(), "chain": chain, "mapped_mutations": mapped}


# ========================================================
# MODULE 5 & 2: PATHWAYS, INTERACTIONS & PROSITE MINING
# ========================================================

@bio_router.post("/motifs/scan")
def api_scan_motifs(
    sequence: str = Query(..., description="Amino acid sequence to scan for PROSITE signatures"),
    settings: Settings = Depends(get_settings),
    client: BioHttpClient = Depends(get_bio_http_client),
) -> dict[str, Any]:
    """Scan amino acid sequence against curated PROSITE regex patterns."""
    from backend.utils.functional_client import FunctionalClient

    func = FunctionalClient(settings=settings, http_client=client)
    hits = func.scan_prosite_motifs(sequence)
    return {"hits": hits, "count": len(hits)}


@bio_router.get("/pathways/{pathway_id}")
def api_get_pathway(
    pathway_id: str,
    settings: Settings = Depends(get_settings),
    client: BioHttpClient = Depends(get_bio_http_client),
) -> dict[str, Any]:
    """Retrieve KEGG pathway metadata."""
    from backend.utils.functional_client import FunctionalClient

    func = FunctionalClient(settings=settings, http_client=client)
    hit = func.get_kegg_pathway(pathway_id)
    if not hit:
        raise HTTPException(status_code=404, detail=f"Pathway '{pathway_id}' not found in KEGG.")
    return hit.model_dump()


@bio_router.get("/interactions/{identifier}")
def api_get_interactions(
    identifier: str,
    species: int = 9606,
    limit: int = 10,
    settings: Settings = Depends(get_settings),
    client: BioHttpClient = Depends(get_bio_http_client),
) -> dict[str, Any]:
    """Retrieve STRING DB protein-protein interaction network."""
    from backend.utils.functional_client import FunctionalClient

    func = FunctionalClient(settings=settings, http_client=client)
    edges = func.get_string_interactions(identifier=identifier, species=species, limit=limit)
    return {"identifier": identifier, "edges": edges, "count": len(edges)}


# ========================================================
# MODULE 6: COMPARATIVE GENOMICS (ENSEMBL, UCSC, GEO)
# ========================================================

@bio_router.get("/locus/{gene_symbol}", response_model=LocusLink)
def api_get_gene_locus(
    gene_symbol: str,
    species: str = "human",
    settings: Settings = Depends(get_settings),
    client: BioHttpClient = Depends(get_bio_http_client),
) -> LocusLink:
    """Retrieve genomic coordinates, Ensembl URL, and UCSC Browser deep-link with archaic tracks."""
    from backend.utils.genomics_client import GenomicsClient

    genomics = GenomicsClient(settings=settings, http_client=client)
    locus = genomics.get_gene_locus(gene_symbol, species=species)
    if not locus:
        raise HTTPException(status_code=404, detail=f"Locus for gene '{gene_symbol}' not found.")
    return locus


# ========================================================
# UNIFIED MULTI-DATABASE LOOKUP (CROSS-REFERENCING)
# ========================================================

@bio_router.get("/lookup/{query}", response_model=BioLookupResponse)
def api_unified_bio_lookup(
    query: str,
    settings: Settings = Depends(get_settings),
    client: BioHttpClient = Depends(get_bio_http_client),
) -> BioLookupResponse:
    """
    Unified multi-database biological lookup:
    Integrates NCBI, UniProt, RCSB PDB, Pfam, PROSITE, KEGG, STRING, and Ensembl
    into a single structured response.
    """
    from backend.utils.bio_aggregator import BioAggregator

    aggregator = BioAggregator(settings=settings, http_client=client)
    return aggregator.lookup(query)
