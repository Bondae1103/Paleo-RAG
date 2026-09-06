"""
bioRxiv ingestion connector, filtered to CC-BY / CC-BY-NC licensed preprints
in the Genomics / Evolutionary Biology collections.

NOT executed live in the build sandbox (api.biorxiv.org was not reachable
from that sandbox's egress allowlist). Structurally complete against
bioRxiv's documented public API (https://api.biorxiv.org/) but unverified
against a live response — verify on the target machine per HANDOFF.md.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx

BIORXIV_DETAILS_URL = "https://api.biorxiv.org/details/biorxiv"
APPROVED_LICENSES = {"cc-by", "cc-by-nc"}
RATE_LIMIT_SECONDS = 0.35
RELEVANT_COLLECTIONS = {"genomics", "evolutionary biology"}


@dataclass
class ManifestRow:
    doc_id: str
    source: str
    license: str
    doi: str
    title: str
    retrieved_at: str
    raw_path: str
    status: str = "downloaded"


def fetch_recent_details(start_cursor: int, http_client: httpx.Client) -> dict:
    """bioRxiv's details endpoint is paginated by date range and cursor.
    A real caller would pick a date range and page through `cursor`; the
    exact pagination contract should be re-verified against the live API
    since it was not exercised in the build sandbox."""
    resp = http_client.get(f"{BIORXIV_DETAILS_URL}/2024-01-01/2024-12-31/{start_cursor}")
    resp.raise_for_status()
    return resp.json()


def ingest_biorxiv(
    limit: int,
    raw_pdf_dir: Path,
    manifest_path: Path,
) -> list[ManifestRow]:
    raw_pdf_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[ManifestRow] = []
    cursor = 0
    with httpx.Client(timeout=20.0) as client:
        while len(rows) < limit:
            time.sleep(RATE_LIMIT_SECONDS)
            try:
                data = fetch_recent_details(cursor, client)
            except httpx.HTTPError as exc:
                print(f"[biorxiv_connector] fetch failed at cursor {cursor}: {exc}")
                break

            collection = data.get("collection", [])
            if not collection:
                break

            for entry in collection:
                if len(rows) >= limit:
                    break
                category = (entry.get("category") or "").lower()
                license_tag = (entry.get("license") or "").lower().replace("_", "-")
                if category not in RELEVANT_COLLECTIONS:
                    continue
                if license_tag not in APPROVED_LICENSES:
                    print(f"[biorxiv_connector] skip {entry.get('doi')}: license '{license_tag}' not approved")
                    continue

                doc_id = entry.get("doi", "").replace("/", "_")
                row = ManifestRow(
                    doc_id=doc_id,
                    source="biorxiv",
                    license=license_tag,
                    doi=entry.get("doi", ""),
                    title=entry.get("title", ""),
                    retrieved_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    raw_path=str(raw_pdf_dir / f"{doc_id}.json"),
                )
                (raw_pdf_dir / f"{doc_id}.json").write_text(json.dumps(entry), encoding="utf-8")
                rows.append(row)

            cursor += len(collection)

    with manifest_path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(asdict(row)) + "\n")

    return rows


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    result_rows = ingest_biorxiv(
        limit=args.limit,
        raw_pdf_dir=Path("data/raw_pdfs"),
        manifest_path=Path("data/processed/manifest.jsonl"),
    )
    print(f"Ingested {len(result_rows)} documents.")
