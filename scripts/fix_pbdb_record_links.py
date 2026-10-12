"""
Fix every PaleoBioDB link in the registry so it opens the specific taxon's
own record instead of the Navigator app's generic homepage.

Audit (2026-10-12): every `fossil_record.pbdb_taxon_id` in the registry was
re-verified against the live PBDB taxa API
(https://paleobiodb.org/data1.2/taxa/single.json?name=<scientific_name>) --
see backend/data/_reports/pbdb_taxon_audit_*.json. All 16 non-null taxon ids
matched the live API exactly (including the two that only resolve at genus
rank in PBDB -- Mylodon and Dinornis -- which the registry already stored
correctly at that rank). No taxon_id values needed correction.

The bug is the URL itself: `pbdb_navigator_url` was hardcoded to
"https://paleobiodb.org/navigator/" (the Navigator SPA's bare landing page)
for every taxon. Investigation found:
  - The Navigator SPA (https://github.com/paleobiodb/navigator) has no
    client-side query-string or hash routing for taxon name/id at all --
    confirmed by reading its deployed assets/js/script.min.js: the only
    `location.hash` handling loads an opaque previously-*saved* state blob
    from `/larkin/app-state?id=<id>`, which requires an interactive "share"
    click server round-trip and has no deterministic taxon-keyed form.
  - PBDB's classic app route `/classic/checkTaxonInfo?taxon_no=<N>` (numeric
    id, no "txn:" prefix) IS a live, working, taxon-specific HTML record
    page -- verified by fetching it for taxon_no=46027 and confirming it
    renders "Mammuthus primigenius (wooly mammoth)" with full classification.
    (A bare curl with no Referer header gets a 403 from PBDB's anti-bot WAF;
    any browser navigating from a real referring page is unaffected.)

This script rewrites `pbdb_navigator_url` (and the unused legacy duplicate
`pbdb` block, kept byte-identical to `fossil_record` as it already was) to
that per-taxon classic record URL for every taxon with a known
`pbdb_taxon_id`, and nulls it for the two taxa (Yersinia pestis, Influenza A
virus) that have no PBDB record at all, rather than linking to the generic
homepage.

Usage:
    python -m scripts.fix_pbdb_record_links
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

REGISTRY_PATHS = [
    ROOT / "backend" / "data" / "paleo_atlas_registry.json",
    ROOT / "frontend" / "client" / "src" / "lib" / "paleo_atlas_registry.json",
]


def record_url(pbdb_taxon_id: str | None) -> str | None:
    if not pbdb_taxon_id:
        return None
    numeric_id = pbdb_taxon_id.split(":", 1)[-1]
    return f"https://paleobiodb.org/classic/checkTaxonInfo?taxon_no={numeric_id}"


def main():
    with open(REGISTRY_PATHS[0], "r", encoding="utf-8") as f:
        registry = json.load(f)

    changed = 0
    for entry in registry:
        for key in ("fossil_record", "pbdb"):
            block = entry.get(key)
            if block is None:
                continue
            new_url = record_url(block.get("pbdb_taxon_id"))
            if block.get("pbdb_navigator_url") != new_url:
                block["pbdb_navigator_url"] = new_url
                changed += 1
            print(f"{entry['tax_id']:15s} [{key:14s}] taxon_id={block.get('pbdb_taxon_id')!s:12s} -> {new_url}")

    for p in REGISTRY_PATHS:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)
        print(f"Wrote: {p}")
    print(f"\nUpdated {changed} pbdb_navigator_url fields.")


if __name__ == "__main__":
    main()
