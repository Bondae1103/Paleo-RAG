"""
Read-only audit of every `fossil_record.pbdb_taxon_id` in the registry
against the live PaleoBiology Database taxa API
(https://paleobiodb.org/data1.2/taxa/single.json?name=<scientific_name>).

Usage:
    python -m scripts.audit_pbdb_taxon_ids
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

REGISTRY_PATH = ROOT / "backend" / "data" / "paleo_atlas_registry.json"
REPORT_DIR = ROOT / "backend" / "data" / "_reports"
PBDB_SINGLE_URL = "https://paleobiodb.org/data1.2/taxa/single.json"


def main():
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)

    client = httpx.Client(timeout=20.0, headers={"User-Agent": "PaleoRAG-audit/1.0 (mukilkrish04@gmail.com)"})
    now = datetime.now(timezone.utc).isoformat()

    records = []
    for entry in registry:
        tax_id = entry["tax_id"]
        name = entry["scientific_name"]
        fr = entry.get("fossil_record", {})
        stored_id = fr.get("pbdb_taxon_id")

        r = client.get(PBDB_SINGLE_URL, params={"name": name})
        time.sleep(0.4)
        live_rec = None
        if r.status_code == 200:
            recs = r.json().get("records", [])
            live_rec = recs[0] if recs else None

        live_id = live_rec.get("oid") if live_rec else None
        live_name = live_rec.get("nam") if live_rec else None
        live_rank = live_rec.get("rnk") if live_rec else None

        if stored_id is None and live_id is None:
            verdict = "confirmed_absent"
        elif stored_id == live_id:
            verdict = "confirmed_match"
        elif stored_id and not live_id:
            # Exact name search found nothing; PBDB may only resolve this
            # taxon at a coarser rank -- either the bare genus (common for
            # monotypic fossil genera) or, for a trinomial subspecies name,
            # the parent binomial species (PBDB does not track subspecies
            # for extant species like archaic Homo sapiens lineages).
            words = name.split(" ")
            fallback_names = [words[0]]
            if len(words) >= 2:
                fallback_names.insert(0, " ".join(words[:2]))
            fallback_rec = None
            fallback_rank_label = None
            for fallback_name, rank_label in zip(fallback_names, ["binomial", "genus"]):
                r2 = client.get(PBDB_SINGLE_URL, params={"name": fallback_name})
                time.sleep(0.4)
                recs2 = r2.json().get("records", []) if r2.status_code == 200 else []
                cand = recs2[0] if recs2 else None
                if cand and cand.get("oid") == stored_id:
                    fallback_rec, fallback_rank_label = cand, rank_label
                    break
            if fallback_rec:
                verdict = f"confirmed_match_at_{fallback_rank_label}_rank"
                live_id, live_name, live_rank = fallback_rec.get("oid"), fallback_rec.get("nam"), fallback_rank_label
            else:
                verdict = "mismatch"
        else:
            verdict = "mismatch"

        rec = {
            "tax_id": tax_id,
            "scientific_name": name,
            "stored_pbdb_taxon_id": stored_id,
            "live_pbdb_taxon_id": live_id,
            "live_name": live_name,
            "live_rank": live_rank,
            "verdict": verdict,
        }
        records.append(rec)
        print(f"[{verdict:28s}] {tax_id:15s} {name:40s} stored={stored_id!s:12s} live={live_id!s:12s} ({live_name})")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"pbdb_taxon_audit_{now[:10]}.json"
    summary = {"generated_at": now, "total_taxa_audited": len(records), "verdict_counts": {}, "records": records}
    for r in records:
        summary["verdict_counts"][r["verdict"]] = summary["verdict_counts"].get(r["verdict"], 0) + 1
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nWrote audit report: {report_path}")
    print(json.dumps(summary["verdict_counts"], indent=2))


if __name__ == "__main__":
    main()
