"""
Read-only audit of every NCBI Nucleotide (nuccore) accession referenced by the
PaleoDB Atlas Registry -- both `extinct_nucleotide_acc` and
`extant_counterpart.extant_nucleotide_acc` fields, at the `target_locus` level
and inside every `molecular_samples[]` entry -- against the live NCBI
E-utilities esummary endpoint.

For every accession site this records the live organism/title NCBI returns
and compares it against the organism the registry claims that site
represents. It never fabricates a replacement accession; it only reports
whether the live record matches, mismatches, or could not be resolved
(e.g. a BioProject ID like "PRJNA285123" is not a nuccore accession at all).

Usage:
    python -m scripts.audit_ncbi_accessions                 # audit only
    python -m scripts.audit_ncbi_accessions --apply          # audit + null out
                                                              # confirmed-wrong
                                                              # accessions in
                                                              # both registry
                                                              # files, with a
                                                              # validation note
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

REGISTRY_PATHS = [
    ROOT / "backend" / "data" / "paleo_atlas_registry.json",
    ROOT / "frontend" / "client" / "src" / "lib" / "paleo_atlas_registry.json",
]
REPORT_DIR = ROOT / "backend" / "data" / "_reports"
ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

# Same convention as scripts/audit_uniprot_accessions.py: a historical-era
# descriptor in parentheses is not a taxonomic qualifier.
ORGANISM_COMPARISON_ALIASES: dict[str, str] = {
    "Yersinia pestis (Bronze Age / Black Death)": "Yersinia pestis",
}

# Archaic/extinct human lineages with no nucleotide record deposited under
# their own name are legitimately deposited under the modern reference
# organism in INSDC practice for ancient-DNA studies of these exact loci.
KNOWN_PROXY_ALLOWLIST: dict[tuple[str, str], set[str]] = {
    ("PRAG-TAX-002", "MC1R"): {"Homo sapiens", "Homo sp. Altai"},
    ("PRAG-TAX-002", "FOXP2"): {"Homo sapiens", "Homo sp. Altai"},
    ("PRAG-TAX-002", "EPAS1"): {"Homo sapiens", "Homo sp. Altai"},
    ("PRAG-TAX-007", "EPAS1"): {"Homo sapiens", "Homo sp. altai"},
    ("PRAG-TAX-007", "TBX15"): {"Homo sapiens"},
    ("PRAG-TAX-007", "FOXP2"): {"Homo sapiens"},
}


def _comparison_organism(name: str | None) -> str | None:
    return ORGANISM_COMPARISON_ALIASES.get(name, name) if name else name


def iter_sites(entry: dict):
    """Yield (path, container, acc_field, gene, expected_organism, tax_id) for every
    nucleotide accession site in one taxon entry."""
    tax_id = entry["tax_id"]
    tl = entry.get("target_locus", {})
    gene = tl.get("gene_symbol")
    if "extinct_nucleotide_acc" in tl:
        yield (f"{tax_id}.target_locus", tl, "extinct_nucleotide_acc", gene, entry.get("scientific_name"), tax_id)
    ec = entry.get("extant_counterpart", {})
    if "extant_nucleotide_acc" in ec:
        yield (f"{tax_id}.extant_counterpart", ec, "extant_nucleotide_acc", gene, ec.get("scientific_name"), tax_id)
    for s in entry.get("molecular_samples", []):
        sid = s.get("sample_id")
        sgene = s.get("gene_symbol")
        if "extinct_nucleotide_acc" in s:
            yield (f"{tax_id}.molecular_samples[{sid}]", s, "extinct_nucleotide_acc", sgene, entry.get("scientific_name"), tax_id)
        ec2 = s.get("extant_counterpart", {})
        if "extant_nucleotide_acc" in ec2:
            yield (f"{tax_id}.molecular_samples[{sid}].extant_counterpart", ec2, "extant_nucleotide_acc", sgene, ec2.get("scientific_name"), tax_id)


def fetch_live(client: httpx.Client, accession: str) -> dict:
    try:
        r = client.get(ESUMMARY_URL, params={"db": "nuccore", "id": accession, "retmode": "json"})
        time.sleep(0.4)
        if r.status_code != 200:
            return {"status": "error", "organism": None, "title": None, "http_status": r.status_code}
        data = r.json()
        result = data.get("result", {})
        uids = result.get("uids", [])
        if not uids:
            return {"status": "not_found", "organism": None, "title": None, "http_status": 200}
        rec = result.get(uids[0], {})
        if rec.get("error"):
            return {"status": "not_found", "organism": None, "title": rec.get("error"), "http_status": 200}
        return {
            "status": "retrieved",
            "organism": rec.get("organism"),
            "title": rec.get("title"),
            "taxid": rec.get("taxid"),
            "accessionversion": rec.get("accessionversion"),
            "http_status": 200,
        }
    except Exception as exc:
        return {"status": "error", "organism": None, "title": None, "error": str(exc), "http_status": None}


def judge(path: str, acc: str, gene: str, expected_organism: str, tax_id: str, live: dict) -> str:
    if not acc:
        return "missing"
    if acc.upper().startswith("PRJNA") or acc.upper().startswith("PRJ"):
        return "invalid_format_not_nuccore_accession"
    if live["status"] != "retrieved":
        return live["status"]
    real_org = (live.get("organism") or "").strip()
    exp = _comparison_organism(expected_organism) or ""
    real_l, exp_l = real_org.lower(), exp.lower()
    title_l = (live.get("title") or "").lower()
    gene_l = (gene or "").lower()
    # A whole-genome/whole-chromosome deposit legitimately won't name any one
    # gene in its title -- it still contains the gene, so organism match
    # alone is sufficient for those. Anything else (a specific mRNA/CDS
    # record) must actually name the gene it claims to represent.
    is_whole_genome_record = any(
        phrase in title_l for phrase in ("complete genome", "complete sequence", "chromosome", "mitochondrion")
    )
    gene_confirmed_in_title = (not gene_l) or is_whole_genome_record or (gene_l in title_l)
    # Strain/isolate/subspecies suffixes (e.g. "Yersinia pestis CO92",
    # "Ceratotherium simum simum") are the same organism at binomial level;
    # NCBI's "organism" field routinely appends them.
    organism_matches = real_l == exp_l or real_l.startswith(exp_l + " ") or exp_l.startswith(real_l + " ")
    if organism_matches:
        if gene_confirmed_in_title:
            return "exact_match"
        return "wrong_gene"
    proxy_set = {p.lower() for p in KNOWN_PROXY_ALLOWLIST.get((tax_id, gene), set())}
    if proxy_set and any(real_l == p or real_l.startswith(p + " ") for p in proxy_set):
        if gene_confirmed_in_title:
            return "proxy_match"
        return "wrong_gene"
    return "wrong_organism"


NEEDS_CORRECTION = {"wrong_organism", "wrong_gene", "invalid_format_not_nuccore_accession", "not_found", "error"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    with open(REGISTRY_PATHS[0], "r", encoding="utf-8") as f:
        registry = json.load(f)

    client = httpx.Client(timeout=20.0, headers={"User-Agent": "PaleoRAG-audit/1.0 (mukilkrish04@gmail.com)"})
    now = datetime.now(timezone.utc).isoformat()

    records = []
    for entry in registry:
        for path, container, field, gene, expected_organism, tax_id in iter_sites(entry):
            acc = container.get(field)
            live = {"status": "skipped_missing", "organism": None, "title": None} if not acc else None
            if acc:
                if acc.upper().startswith("PRJNA") or acc.upper().startswith("PRJ"):
                    live = {"status": "invalid_format", "organism": None, "title": "BioProject ID, not a nuccore accession"}
                else:
                    live = fetch_live(client, acc)
            verdict = judge(path, acc, gene, expected_organism, tax_id, live)
            rec = {
                "path": path,
                "tax_id": tax_id,
                "field": field,
                "accession": acc,
                "gene": gene,
                "expected_organism": expected_organism,
                "live_organism": live.get("organism"),
                "live_title": live.get("title"),
                "live_taxid": live.get("taxid"),
                "verdict": verdict,
            }
            records.append(rec)
            print(f"[{verdict:32s}] {path:55s} acc={acc!s:14s} expected={expected_organism!r:35s} live_org={live.get('organism')!r}")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"ncbi_accession_audit_{now[:10]}.json"
    summary = {
        "generated_at": now,
        "total_sites_audited": len(records),
        "verdict_counts": {},
        "records": records,
    }
    for r in records:
        v = r["verdict"]
        summary["verdict_counts"][v] = summary["verdict_counts"].get(v, 0) + 1
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nWrote audit report: {report_path}")
    print(json.dumps(summary["verdict_counts"], indent=2))

    if not args.apply:
        print("\n(read-only run; pass --apply to write corrections into the registry)")
        return

    corrected = 0
    for entry in registry:
        for path, container, field, gene, expected_organism, tax_id in iter_sites(entry):
            match = next((r for r in records if r["path"] == path and r["field"] == field), None)
            if not match:
                continue
            v = match["verdict"]
            val_field = field.replace("_acc", "_validation")
            if v in ("exact_match", "proxy_match"):
                container[val_field] = {
                    "status": "verified_exact" if v == "exact_match" else "verified_proxy",
                    "checked_organism": match["live_organism"],
                    "checked_taxid": match["live_taxid"],
                    "evidence_source": f"https://www.ncbi.nlm.nih.gov/nuccore/{match['accession']}",
                    "validated_at": now,
                    "note": None,
                }
            elif v in NEEDS_CORRECTION:
                container[val_field] = {
                    "status": "unverified",
                    "checked_organism": match["live_organism"],
                    "checked_taxid": match["live_taxid"],
                    "evidence_source": f"https://www.ncbi.nlm.nih.gov/nuccore/{match['accession']}" if match["accession"] else None,
                    "validated_at": now,
                    "previous_accession": match["accession"],
                    "note": f"Live NCBI lookup verdict={v}; original accession does not verifiably represent {expected_organism!r}. Nulled rather than left pointing at the wrong record.",
                }
                container[field] = None
                corrected += 1

    for p in REGISTRY_PATHS:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)
        print(f"Wrote corrected registry: {p}")
    print(f"\nNulled (unverified): {corrected}")


if __name__ == "__main__":
    main()
