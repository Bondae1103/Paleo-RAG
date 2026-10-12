"""
Read-only retrieval audit of extant-counterpart sequences for the 18 PaleoDB
Atlas taxa, against the live NCBI Nucleotide (E-utilities) and UniProtKB REST
APIs.

For every taxon's `extant_counterpart` block, this script:
  - Looks up `extant_nucleotide_acc` against NCBI Nucleotide (nuccore) via
    `NCBIClient.get_sequence_record`.
  - Looks up `extant_uniprot_acc` against UniProtKB via `UniProtClient.get_protein`.
  - Records accession.version, source organism, gene symbol(s), sequence,
    database URL, and retrieval status for each.
  - Never fabricates a record: a missing accession or a failed live lookup is
    marked "unresolved" with the reason, and no replacement is invented.

This script makes NO writes to the registry. It only writes a new audit
report under backend/data/_reports/.

Usage:
    python -m scripts.audit_extant_sequences
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backend.utils.error_types import DatabaseClientError, DatabaseNotFoundError  # noqa: E402
from backend.utils.ncbi_client import NCBIClient  # noqa: E402
from backend.utils.uniprot_client import UniProtClient  # noqa: E402

REGISTRY_PATH = ROOT / "backend" / "data" / "paleo_atlas_registry.json"
REPORT_DIR = ROOT / "backend" / "data" / "_reports"


def fetch_ncbi(ncbi: NCBIClient, accession: str) -> dict:
    url = f"https://www.ncbi.nlm.nih.gov/nuccore/{accession}"
    try:
        rec = ncbi.get_sequence_record(accession)
        return {
            "status": "retrieved",
            "accession_queried": accession,
            "accession_version": rec.id,
            "organism": rec.annotations.get("organism"),
            "description": rec.description,
            "sequence": rec.sequence,
            "length": rec.length,
            "database_url": url,
            "error": None,
        }
    except DatabaseNotFoundError as exc:
        return {
            "status": "unresolved",
            "accession_queried": accession,
            "accession_version": None,
            "organism": None,
            "description": None,
            "sequence": None,
            "length": None,
            "database_url": url,
            "error": f"not found in NCBI Nucleotide: {exc}",
        }
    except Exception as exc:
        return {
            "status": "unresolved",
            "accession_queried": accession,
            "accession_version": None,
            "organism": None,
            "description": None,
            "sequence": None,
            "length": None,
            "database_url": url,
            "error": f"NCBI lookup failed: {exc}",
        }


def fetch_uniprot(uniprot: UniProtClient, accession: str) -> dict:
    clean_acc = accession.strip().upper()
    url = f"https://rest.uniprot.org/uniprotkb/{clean_acc}"
    try:
        raw = uniprot.http.get_json(f"{url}.json")
        version = raw.get("entryAudit", {}).get("sequenceVersion")
        rec = uniprot._normalize_entry(raw)
        return {
            "status": "retrieved",
            "accession_queried": accession,
            "accession_version": f"{rec.accession}.{version}" if version else rec.accession,
            "entry_name": rec.entry_name,
            "organism": rec.organism,
            "organism_id": rec.organism_id,
            "gene_symbols": rec.gene_symbols,
            "protein_name": rec.protein_name,
            "reviewed": rec.reviewed,
            "sequence": rec.sequence,
            "length": rec.length,
            "database_url": url,
            "error": None,
        }
    except DatabaseNotFoundError as exc:
        return {
            "status": "unresolved",
            "accession_queried": accession,
            "accession_version": None,
            "entry_name": None,
            "organism": None,
            "organism_id": None,
            "gene_symbols": [],
            "protein_name": None,
            "reviewed": None,
            "sequence": None,
            "length": None,
            "database_url": url,
            "error": f"not found in UniProtKB: {exc}",
        }
    except Exception as exc:
        return {
            "status": "unresolved",
            "accession_queried": accession,
            "accession_version": None,
            "entry_name": None,
            "organism": None,
            "organism_id": None,
            "gene_symbols": [],
            "protein_name": None,
            "reviewed": None,
            "sequence": None,
            "length": None,
            "database_url": url,
            "error": f"UniProt lookup failed: {exc}",
        }


def main():
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)

    ncbi = NCBIClient()
    uniprot = UniProtClient()
    now = datetime.now(timezone.utc).isoformat()

    results = []
    for entry in registry:
        tax_id = entry["tax_id"]
        scientific_name = entry.get("scientific_name")
        tl = entry.get("target_locus", {})
        gene_symbol = tl.get("gene_symbol")
        ec = entry.get("extant_counterpart", {})

        rec = {
            "tax_id": tax_id,
            "extinct_scientific_name": scientific_name,
            "gene_symbol": gene_symbol,
            "extant_common_name": ec.get("common_name"),
            "extant_scientific_name": ec.get("scientific_name"),
            "registry_extant_nucleotide_acc": ec.get("extant_nucleotide_acc"),
            "registry_extant_uniprot_acc": ec.get("extant_uniprot_acc"),
            "registry_sequence_dna_present": bool(ec.get("extant_sequence_dna")),
            "registry_sequence_aa_present": bool(ec.get("extant_sequence_aa")),
        }

        nuc_acc = ec.get("extant_nucleotide_acc")
        if nuc_acc:
            ncbi_result = fetch_ncbi(ncbi, nuc_acc)
        else:
            ncbi_result = {
                "status": "unresolved",
                "accession_queried": None,
                "error": "no extant_nucleotide_acc in registry for this taxon",
            }
        rec["ncbi_nucleotide"] = ncbi_result

        if ncbi_result.get("status") == "retrieved" and ec.get("extant_sequence_dna"):
            rec["dna_sequence_matches_registry"] = (
                ncbi_result["sequence"].upper() == ec["extant_sequence_dna"].upper()
            )
        else:
            rec["dna_sequence_matches_registry"] = None

        up_acc = ec.get("extant_uniprot_acc")
        if up_acc:
            uniprot_result = fetch_uniprot(uniprot, up_acc)
        else:
            uniprot_result = {
                "status": "unresolved",
                "accession_queried": None,
                "error": "no extant_uniprot_acc in registry for this taxon",
            }
        rec["uniprot_protein"] = uniprot_result

        if uniprot_result.get("status") == "retrieved" and ec.get("extant_sequence_aa"):
            rec["aa_sequence_matches_registry"] = (
                uniprot_result["sequence"].upper() == ec["extant_sequence_aa"].upper()
            )
        else:
            rec["aa_sequence_matches_registry"] = None

        results.append(rec)
        print(
            f"{tax_id:14s} gene={gene_symbol or '-':8s} "
            f"NCBI[{ncbi_result['status']}] acc={nuc_acc} "
            f"UniProt[{uniprot_result['status']}] acc={up_acc}"
        )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"extant_sequence_audit_{now[:10]}.json"
    summary = {
        "generated_at": now,
        "total_taxa": len(results),
        "ncbi_status_counts": {},
        "uniprot_status_counts": {},
        "records": results,
    }
    for r in results:
        ns = r["ncbi_nucleotide"]["status"]
        us = r["uniprot_protein"]["status"]
        summary["ncbi_status_counts"][ns] = summary["ncbi_status_counts"].get(ns, 0) + 1
        summary["uniprot_status_counts"][us] = summary["uniprot_status_counts"].get(us, 0) + 1

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nWrote audit report: {report_path}")
    print("NCBI status counts:", json.dumps(summary["ncbi_status_counts"], indent=2))
    print("UniProt status counts:", json.dumps(summary["uniprot_status_counts"], indent=2))


if __name__ == "__main__":
    main()
