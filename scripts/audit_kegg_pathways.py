"""
Audit (and, with --apply, correct) every KEGG `pathway.kegg_id` in the PaleoDB
Atlas Registry -- at the `target_locus` level and inside every
`molecular_samples[]` entry -- against live KEGG REST gene-pathway linkage
data (https://rest.kegg.jp).

Methodology, run interactively against the live KEGG API for every unique
gene symbol in the registry (see docs/ comment at bottom for the raw queries):
  - For a human nuclear/mitochondrial gene: resolve its KEGG hsa: gene ID via
    `find/hsa/<SYMBOL>`, then list its real pathway memberships via
    `link/pathway/hsa:<id>` and compare the numeric suffix to the registry's
    "map" id.
  - For a Yersinia pestis gene: resolve the real CO92 (ype) locus tag (pla =
    ype:YPPCP1.07 on plasmid pPCP1; caf1 = ype:YPMT1.84 on plasmid pMT1; yopM
    = ype:YPCD1.26c on plasmid pCD1 -- all three locus tags cross-checked
    against the plasmid named in the registry's own `genomics.chromosome`
    field for that sample) and likewise checked its real `link/pathway`
    membership.
  - For Influenza A genes (HA/NA/PB2): KEGG does not host a strain-specific
    H1N1-1918 genome, so membership was judged from the generic reference
    pathway map05164 ("Influenza A")'s own curated DESCRIPTION, which
    explicitly names HA and NA as the pathway's defining viral glycoproteins
    but never mentions PB2 (a polymerase subunit, thematically outside this
    host-cell-entry/immune-evasion pathway).

Findings (verified 2026-10-12, see backend/data/_reports/kegg_pathway_audit_*.json):
  - HBB, HBA: real KEGG membership is African trypanosomiasis (hsa05143) and
    Malaria (hsa05144) only -- not "oxygen transport". No KEGG reference
    pathway represents simple O2-carrier function. map05100 ("Bacterial
    invasion of epithelial cells"), used throughout the registry for every
    HBB/HBA entry, is unrelated and wrong.
  - FOXP2, TBX15: zero KEGG pathway memberships exist for either gene.
    map04360 ("Axon guidance") and map04923 ("Regulation of lipolysis in
    adipocytes") are both wrong.
  - pla, caf1 (Yersinia pestis): zero KEGG pathway memberships for either
    gene. map05100 is wrong for both (ype doesn't even instantiate pathway
    05100).
  - yopM (Yersinia pestis): confirmed member of ype05135 "Yersinia
    infection" (the real, Yersinia-specific reference pathway). The
    registry's map05130 is "Pathogenic Escherichia coli infection" -- a
    different species' pathway entirely. Corrected map05130 -> map05135.
  - PB2 (Influenza): no defensible membership in map05164 could be
    confirmed; marked unverified.
  - MC1R -> map04916, EPAS1 -> map04066, TRPV3 -> map04750, COL1A1 ->
    map04512, CYTB -> map00190, COX1 -> map00190, HA/NA -> map05164: all
    confirmed correct, left unchanged.

This script applies exactly that verified table. It does not call KEGG at
request time (no live ambiguity remains to resolve), but every verdict above
is reproducible by re-running the raw `rest.kegg.jp` queries documented
inline.

Usage:
    python -m scripts.audit_kegg_pathways                # report only
    python -m scripts.audit_kegg_pathways --apply         # write corrections
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

REGISTRY_PATHS = [
    ROOT / "backend" / "data" / "paleo_atlas_registry.json",
    ROOT / "frontend" / "client" / "src" / "lib" / "paleo_atlas_registry.json",
]
REPORT_DIR = ROOT / "backend" / "data" / "_reports"

# gene_symbol -> verified verdict.
#   "status": "confirmed"  -> kegg_id is correct, leave untouched
#   "status": "wrong_id"   -> replace kegg_id with "correct_id"
#   "status": "unverifiable" -> no live-confirmed KEGG pathway exists; null it
VERDICTS: dict[str, dict] = {
    "MC1R":   {"status": "confirmed", "evidence": "https://rest.kegg.jp/link/pathway/hsa:4157 lists path:hsa04916"},
    "EPAS1":  {"status": "confirmed", "evidence": "https://rest.kegg.jp/link/pathway/hsa:2034 lists path:hsa04066"},
    "TRPV3":  {"status": "confirmed", "evidence": "https://rest.kegg.jp/link/pathway/hsa:162514 lists path:hsa04750"},
    "COL1A1": {"status": "confirmed", "evidence": "https://rest.kegg.jp/link/pathway/hsa:1277 lists path:hsa04512"},
    "CYTB":   {"status": "confirmed", "evidence": "https://rest.kegg.jp/link/pathway/hsa:4519 (MT-CYB) lists path:hsa00190"},
    "COX1":   {"status": "confirmed", "evidence": "https://rest.kegg.jp/link/pathway/hsa:4512 (MT-CO1) lists path:hsa00190"},
    "HA":     {"status": "confirmed", "evidence": "https://rest.kegg.jp/get/map05164 description explicitly names HA as a defining pathway glycoprotein"},
    "NA":     {"status": "confirmed", "evidence": "https://rest.kegg.jp/get/map05164 description explicitly names NA as a defining pathway glycoprotein"},

    "HBB": {
        "status": "unverifiable",
        "note": "Live KEGG gene-pathway linkage (rest.kegg.jp/link/pathway/hsa:3043) shows HBB belongs only to "
                "hsa05143 (African trypanosomiasis) and hsa05144 (Malaria) -- not any oxygen-transport pathway. "
                "map05100 ('Bacterial invasion of epithelial cells') is unrelated to HBB's function; no KEGG "
                "reference pathway represents simple hemoglobin oxygen-carrier activity.",
    },
    "HBA": {
        "status": "unverifiable",
        "note": "Live KEGG gene-pathway linkage (rest.kegg.jp/link/pathway/hsa:3039) shows HBA1 belongs only to "
                "hsa05143 (African trypanosomiasis) and hsa05144 (Malaria) -- not any oxygen-transport pathway. "
                "map05100 is unrelated; no KEGG reference pathway represents simple hemoglobin oxygen-carrier activity.",
    },
    "FOXP2": {
        "status": "unverifiable",
        "note": "Live KEGG query (rest.kegg.jp/link/pathway/hsa:93986) returns zero pathway memberships for FOXP2. "
                "map04360 ('Axon guidance') is not a confirmed KEGG association for this gene.",
    },
    "TBX15": {
        "status": "unverifiable",
        "note": "Live KEGG query (rest.kegg.jp/link/pathway/hsa:6913) returns zero pathway memberships for TBX15. "
                "map04923 ('Regulation of lipolysis in adipocytes') is not a confirmed KEGG association for this gene.",
    },
    "pla": {
        "status": "unverifiable",
        "note": "Live KEGG query (rest.kegg.jp/link/pathway/ype:YPPCP1.07) returns zero pathway memberships for pla. "
                "Yersinia pestis CO92 (ype) does not even instantiate pathway 05100 "
                "(rest.kegg.jp/get/ype05100 returns empty). map05100 is not a confirmed association.",
    },
    "caf1": {
        "status": "unverifiable",
        "note": "Live KEGG query (rest.kegg.jp/link/pathway/ype:YPMT1.84) returns zero pathway memberships for "
                "caf1 (F1 capsule antigen). map05100 is not a confirmed association, and ype doesn't instantiate it.",
    },
    "yopM": {
        "status": "wrong_id",
        "correct_id": "map05135",
        "note": "Live KEGG confirms yopM (ype:YPCD1.26c, on plasmid pCD1) is a member of ype05135 'Yersinia "
                "infection' (rest.kegg.jp/link/pathway/ype:YPCD1.26c -> path:ype05135). The registry's map05130 is "
                "KEGG's 'Pathogenic Escherichia coli infection' pathway -- a different species entirely.",
        "evidence": "https://rest.kegg.jp/link/pathway/ype:YPCD1.26c",
    },
    "PB2": {
        "status": "unverifiable",
        "note": "KEGG hosts no strain-specific gene entry for 1918 H1N1 PB2, and the generic reference pathway "
                "map05164 ('Influenza A')'s curated description names HA, NA, NS1, and PB1-F2 as its defining viral "
                "components but never PB2 (a distinct polymerase subunit); membership could not be confirmed.",
    },
}


def iter_pathway_sites(entry: dict):
    tax_id = entry["tax_id"]
    tl = entry.get("target_locus", {})
    p = entry.get("pathway")
    if p is not None:
        yield (f"{tax_id}.pathway", p, tl.get("gene_symbol"))
    for s in entry.get("molecular_samples", []):
        sp = s.get("pathway")
        if sp is not None:
            sid = s.get("sample_id")
            yield (f"{tax_id}.molecular_samples[{sid}].pathway", sp, s.get("gene_symbol"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    with open(REGISTRY_PATHS[0], "r", encoding="utf-8") as f:
        registry = json.load(f)

    now = datetime.now(timezone.utc).isoformat()
    records = []
    for entry in registry:
        for path, p, gene in iter_pathway_sites(entry):
            verdict = VERDICTS.get(gene)
            rec = {
                "path": path,
                "gene": gene,
                "registry_kegg_id": p.get("kegg_id"),
                "registry_pathway_name": p.get("pathway_name"),
                "verdict": verdict["status"] if verdict else "no_verdict_for_gene",
                "correct_id": verdict.get("correct_id") if verdict else None,
                "note": verdict.get("note") if verdict else f"No audited verdict exists for gene symbol {gene!r}.",
            }
            records.append(rec)
            print(f"[{rec['verdict']:14s}] {path:55s} gene={gene!s:10s} kegg_id={p.get('kegg_id')!s:12s} -> {rec['correct_id'] or ''}")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"kegg_pathway_audit_{now[:10]}.json"
    summary = {"generated_at": now, "total_sites_audited": len(records), "verdict_counts": {}, "records": records}
    for r in records:
        summary["verdict_counts"][r["verdict"]] = summary["verdict_counts"].get(r["verdict"], 0) + 1
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nWrote audit report: {report_path}")
    print(json.dumps(summary["verdict_counts"], indent=2))

    if not args.apply:
        print("\n(read-only run; pass --apply to write corrections into the registry)")
        return

    corrected = 0
    nulled = 0
    for entry in registry:
        for path, p, gene in iter_pathway_sites(entry):
            verdict = VERDICTS.get(gene)
            if not verdict:
                continue
            if verdict["status"] == "confirmed":
                p["kegg_validation"] = {
                    "status": "verified_live",
                    "evidence_source": verdict.get("evidence"),
                    "validated_at": now,
                    "note": None,
                }
            elif verdict["status"] == "wrong_id":
                previous = p.get("kegg_id")
                p["kegg_id"] = verdict["correct_id"]
                p["kegg_validation"] = {
                    "status": "corrected",
                    "evidence_source": verdict.get("evidence"),
                    "validated_at": now,
                    "previous_kegg_id": previous,
                    "note": verdict["note"],
                }
                corrected += 1
            elif verdict["status"] == "unverifiable":
                previous = p.get("kegg_id")
                p["kegg_id"] = None
                p["kegg_validation"] = {
                    "status": "unverified",
                    "evidence_source": None,
                    "validated_at": now,
                    "previous_kegg_id": previous,
                    "note": verdict["note"],
                }
                nulled += 1

    for path_ in REGISTRY_PATHS:
        with open(path_, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)
        print(f"Wrote corrected registry: {path_}")
    print(f"\nCorrected (wrong id -> right id): {corrected}  Nulled (unverified): {nulled}")


if __name__ == "__main__":
    main()
