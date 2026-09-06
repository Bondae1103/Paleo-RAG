"""
Paleobiology Database (PBDB) connector — pulls STRUCTURED occurrence/taxonomy
data (not free text) for use as query-time payload-filter metadata (taxon
name -> geological period joins), per the implementation plan. This data is
NOT chunked into the RAG corpus; it augments chunk payloads in Qdrant.

NOT executed live in the build sandbox (paleobiodb.org not reachable from
that sandbox's egress allowlist). Structurally complete against PBDB's
documented data1.2 API but unverified against a live response — verify on
the target machine per HANDOFF.md.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

PBDB_TAXA_URL = "https://paleobiodb.org/data1.2/taxa/list.json"
RATE_LIMIT_SECONDS = 0.5


def fetch_taxon_occurrences(taxon_name: str, http_client: httpx.Client) -> list[dict]:
    resp = http_client.get(PBDB_TAXA_URL, params={"name": taxon_name, "show": "phylo,ecospace"})
    resp.raise_for_status()
    data = resp.json()
    return data.get("records", [])


def build_taxon_period_index(taxon_names: list[str], output_path: Path) -> dict[str, str]:
    """Build a {scientific_name: geological_period} lookup, written to disk
    so it can be joined at ingest time when tagging chunk payloads with
    `geological_period`, without a live PBDB call per document."""
    index: dict[str, str] = {}
    with httpx.Client(timeout=20.0) as client:
        for name in taxon_names:
            time.sleep(RATE_LIMIT_SECONDS)
            try:
                records = fetch_taxon_occurrences(name, client)
            except httpx.HTTPError as exc:
                print(f"[pbdb_connector] skip {name}: {exc}")
                continue
            if not records:
                continue
            record = records[0]
            period = record.get("early_interval") or record.get("oei")
            if period:
                index[name] = period

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    return index


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--taxa", nargs="+", required=True)
    parser.add_argument("--output", default="data/processed/taxon_period_index.json")
    args = parser.parse_args()

    result = build_taxon_period_index(args.taxa, Path(args.output))
    print(f"Resolved geological periods for {len(result)}/{len(args.taxa)} taxa.")
