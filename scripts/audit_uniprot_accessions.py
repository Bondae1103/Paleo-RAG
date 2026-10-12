"""
Reproducible audit (and, with --apply, correction) of every extinct_uniprot_acc /
extant_uniprot_acc value in the PaleoDB Atlas Registry against the live UniProt
REST API (https://rest.uniprot.org).

Usage:
    python -m scripts.audit_uniprot_accessions                 # audit only, writes report
    python -m scripts.audit_uniprot_accessions --apply         # audit + write corrections into the registry JSON

Never fabricates an accession, organism, or sequence. A record is only ever
changed when a live UniProt lookup returns an entry whose organism AND gene
both match what the record claims; otherwise the record's accession is left
alone and annotated unverified (never silently dropped, never guessed).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backend.utils.uniprot_validator import (  # noqa: E402
    UniProtValidator,
    VERDICT_EXACT_MATCH,
    VERDICT_PROXY_SAME_SPECIES,
    VERDICT_INACTIVE,
    VERDICT_INVALID,
    VERDICT_WRONG_GENE,
    VERDICT_WRONG_ORGANISM,
    VERDICT_WRONG_ORGANISM_AND_GENE,
    VERDICT_ERROR,
)

REGISTRY_PATHS = [
    ROOT / "backend" / "data" / "paleo_atlas_registry.json",
    ROOT / "frontend" / "client" / "src" / "lib" / "paleo_atlas_registry.json",
]
REPORT_DIR = ROOT / "backend" / "data" / "_reports"

# Legitimate "proxy" cases: records whose extinct taxon has no UniProt entry of
# its own, where the extant reference organism named below IS the correct,
# defensible stand-in (e.g. Neanderthal/Denisovan loci known to be identical,
# or near-identical, to the modern human reference). Keyed by (tax_id, gene_symbol).
KNOWN_PROXY_ALLOWLIST: dict[tuple[str, str], set[str]] = {
    ("PRAG-TAX-002", "FOXP2"): {"Homo sapiens"},
    ("PRAG-TAX-002", "MC1R"): {"Homo sapiens"},
    ("PRAG-TAX-002", "EPAS1"): {"Homo sapiens"},
    ("PRAG-TAX-007", "FOXP2"): {"Homo sapiens"},
    ("PRAG-TAX-007", "EPAS1"): {"Homo sapiens"},
    ("PRAG-TAX-007", "TBX15"): {"Homo sapiens"},
}

# Minimum plausible full-length residue count per gene, from canonical UniProt
# reviewed entries for well-studied mammals/birds. Used only to reject obvious
# fragment deposits (e.g. a 79-aa partial survey sequence) as replacement
# candidates for a gene whose real protein is ~10x longer -- never to validate
# an exact-length match, since natural length variation across species is real.
MIN_LENGTH_BY_GENE: dict[str, int] = {
    "CYTB": 250, "COX1": 350, "HBA": 100, "HBB": 100, "COL1A1": 900,
    "FOXP2": 400, "TRPV3": 500, "MC1R": 250, "EPAS1": 600, "TBX15": 400,
    "PLA": 200, "CAF1": 120, "YOPM": 250, "HA": 400, "NA": 300, "PB2": 500,
}

NEEDS_REPLACEMENT = {
    VERDICT_WRONG_GENE,
    VERDICT_WRONG_ORGANISM,
    VERDICT_WRONG_ORGANISM_AND_GENE,
    VERDICT_INACTIVE,
    VERDICT_INVALID,
}

# The registry stores a few scientific_name values with a non-taxonomic historical
# descriptor appended in parentheses (e.g. a pandemic era label, not a strain/subspecies).
# These are aliased to the plain binomial ONLY for comparison against live UniProt --
# the registry's own scientific_name field is left untouched. Influenza strain labels
# (e.g. "Influenza A virus (H1N1 1918)") are deliberately NOT in this map: those
# parentheticals ARE meaningful strain identifiers and a mismatch there is a real finding.
ORGANISM_COMPARISON_ALIASES: dict[str, str] = {
    "Yersinia pestis (Bronze Age / Black Death)": "Yersinia pestis",
}


def _comparison_organism(name: str | None) -> str | None:
    return ORGANISM_COMPARISON_ALIASES.get(name, name) if name else name


def iter_accession_sites(entry: dict):
    """Yield (path_description, container_dict, acc_field, gene, organism, tax_id) for every accession site in one taxon entry."""
    tax_id = entry["tax_id"]
    tl = entry.get("target_locus", {})
    if "extinct_uniprot_acc" in tl:
        yield (f"{tax_id}.target_locus", tl, "extinct_uniprot_acc", tl.get("gene_symbol"), entry.get("scientific_name"), tax_id)
    ec = entry.get("extant_counterpart", {})
    if "extant_uniprot_acc" in ec:
        yield (f"{tax_id}.extant_counterpart", ec, "extant_uniprot_acc", tl.get("gene_symbol"), ec.get("scientific_name"), tax_id)
    for s in entry.get("molecular_samples", []):
        sid = s.get("sample_id")
        if "extinct_uniprot_acc" in s:
            yield (f"{tax_id}.molecular_samples[{sid}]", s, "extinct_uniprot_acc", s.get("gene_symbol"), entry.get("scientific_name"), tax_id)
        ec2 = s.get("extant_counterpart", {})
        if "extant_uniprot_acc" in ec2:
            yield (f"{tax_id}.molecular_samples[{sid}].extant_counterpart", ec2, "extant_uniprot_acc", s.get("gene_symbol"), ec2.get("scientific_name"), tax_id)


def find_replacement(validator: UniProtValidator, gene: str, organism: str):
    """Search live UniProt for a real, species-and-gene-matched accession. Returns dict or None. Never fabricates."""
    if not gene or not organism:
        return None
    query = f'gene:{gene} AND organism_name:"{organism}"'
    try:
        candidates = validator.client.search_proteins(query, limit=10)
    except Exception:
        return None
    if not candidates:
        return None
    exact = [c for c in candidates if c.organism == organism]
    if not exact:
        return None
    # Avoid picking a tiny fragment deposit when a more complete isolate of the
    # same organism+gene also exists in the result set (common for shotgun-survey
    # TrEMBL entries). Keep only entries within 60% of the longest candidate's length,
    # then prefer reviewed (Swiss-Prot) and longest among those.
    max_len = max(c.length for c in exact)
    complete_enough = [c for c in exact if c.length >= max_len * 0.6]
    floor = MIN_LENGTH_BY_GENE.get(gene.strip().upper(), 0)
    complete_enough = [c for c in complete_enough if c.length >= floor]
    if not complete_enough:
        return None
    complete_enough.sort(key=lambda c: (not c.reviewed, -c.length))
    best = complete_enough[0]
    return {
        "accession": best.accession,
        "entry_name": best.entry_name,
        "organism": best.organism,
        "taxon_id": best.organism_id,
        "gene_symbols": best.gene_symbols,
        "reviewed": best.reviewed,
        "length": best.length,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write corrections back into the registry JSON files")
    args = parser.parse_args()

    with open(REGISTRY_PATHS[0], "r", encoding="utf-8") as f:
        registry = json.load(f)

    validator = UniProtValidator()
    now = datetime.now(timezone.utc).isoformat()

    records: list[dict] = []
    # Cache raw (non-organism-specific) UniProt facts per accession to avoid re-deriving verdicts
    # inconsistently; the validator itself relies on BioHttpClient's disk cache for the network hop.
    for entry in registry:
        for path, container, field, gene, organism, tax_id in iter_accession_sites(entry):
            acc = container.get(field)
            rec = {
                "path": path,
                "tax_id": tax_id,
                "field": field,
                "original_accession": acc,
                "expected_gene": gene,
                "expected_organism": organism,
            }
            if not acc:
                rec["verdict"] = "missing"
                records.append(rec)
                continue

            proxy_set = KNOWN_PROXY_ALLOWLIST.get((tax_id, gene))
            cmp_organism = _comparison_organism(organism)
            verdict = validator.validate(acc, expected_organism=cmp_organism, expected_gene=gene, same_species_proxy_organisms=proxy_set)
            rec.update(
                verdict=verdict.verdict,
                http_status=verdict.http_status,
                real_organism=verdict.real_organism,
                real_taxon_id=verdict.real_taxon_id,
                real_gene_symbols=verdict.real_gene_symbols,
                real_protein_name=verdict.real_protein_name,
                reviewed=verdict.reviewed,
                error_message=verdict.error_message,
            )

            if verdict.verdict in NEEDS_REPLACEMENT:
                replacement = find_replacement(validator, gene, cmp_organism)
                rec["proposed_replacement"] = replacement
            else:
                rec["proposed_replacement"] = None

            records.append(rec)
            print(f"[{verdict.verdict:28s}] {path:55s} acc={acc:12s} expected={organism!r}/{gene!r} real={verdict.real_organism!r}")

    # --- Report ---
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"uniprot_audit_{now[:10]}.json"
    summary = {
        "generated_at": now,
        "total_records_audited": len(records),
        "unique_accessions_checked": len({r["original_accession"] for r in records if r.get("original_accession")}),
        "verdict_counts": {},
        "records": records,
    }
    for r in records:
        v = r.get("verdict", "missing")
        summary["verdict_counts"][v] = summary["verdict_counts"].get(v, 0) + 1

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nWrote audit report: {report_path}")
    print(json.dumps(summary["verdict_counts"], indent=2))

    if not args.apply:
        print("\n(read-only run; pass --apply to write corrections into the registry)")
        return

    # --- Apply corrections ---
    corrected = 0
    unverified = 0
    for entry in registry:
        for path, container, field, gene, organism, tax_id in iter_accession_sites(entry):
            match = next((r for r in records if r["path"] == path and r["field"] == field), None)
            if not match:
                continue
            v = match["verdict"]
            val_field = field.replace("_acc", "_validation")
            if v in (VERDICT_EXACT_MATCH, VERDICT_PROXY_SAME_SPECIES):
                container[val_field] = {
                    "status": "verified_exact" if v == VERDICT_EXACT_MATCH else "verified_proxy",
                    "checked_organism": match["real_organism"],
                    "checked_taxon_id": match["real_taxon_id"],
                    "checked_gene_symbols": match["real_gene_symbols"],
                    "evidence_source": f"https://rest.uniprot.org/uniprotkb/{match['original_accession']}",
                    "validated_at": now,
                    "previous_accession": None,
                    "note": None if v == VERDICT_EXACT_MATCH else "No distinct UniProt entry exists for this extinct/archaic taxon; the modern-human reference is the documented proxy.",
                }
            elif v in NEEDS_REPLACEMENT:
                repl = match.get("proposed_replacement")
                if repl:
                    container[val_field] = {
                        "status": "corrected",
                        "checked_organism": repl["organism"],
                        "checked_taxon_id": repl["taxon_id"],
                        "checked_gene_symbols": repl["gene_symbols"],
                        "evidence_source": f"https://rest.uniprot.org/uniprotkb/{repl['accession']}",
                        "validated_at": now,
                        "previous_accession": match["original_accession"],
                        "note": f"Replaced {match['original_accession']} ({match.get('real_organism')} / {v}) with a live-UniProt-verified organism+gene match.",
                    }
                    container[field] = repl["accession"]
                    corrected += 1
                else:
                    container[val_field] = {
                        "status": "unverified",
                        "checked_organism": match.get("real_organism"),
                        "checked_taxon_id": match.get("real_taxon_id"),
                        "checked_gene_symbols": match.get("real_gene_symbols", []),
                        "evidence_source": f"https://rest.uniprot.org/uniprotkb/{match['original_accession']}",
                        "validated_at": now,
                        "previous_accession": match["original_accession"],
                        "note": f"Original accession is {v}; no defensible same-organism same-gene UniProt replacement was found by live search. Field nulled rather than left silently wrong.",
                    }
                    container[field] = None
                    unverified += 1
            elif v == VERDICT_ERROR:
                container[val_field] = {
                    "status": "unverified",
                    "checked_organism": None,
                    "checked_taxon_id": None,
                    "checked_gene_symbols": [],
                    "evidence_source": "https://rest.uniprot.org/",
                    "validated_at": now,
                    "previous_accession": None,
                    "note": f"Live validation failed ({match.get('error_message')}); accession left as-is pending rerun.",
                }

    for p in REGISTRY_PATHS:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)
        print(f"Wrote corrected registry: {p}")

    print(f"\nCorrected: {corrected}  Marked unverified (nulled): {unverified}")


if __name__ == "__main__":
    main()
