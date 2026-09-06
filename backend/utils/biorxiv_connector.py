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
    publication_year: Optional[int] = None
    taxon_scientific_name: Optional[str] = None
    geological_period: Optional[str] = None


def fetch_recent_details(start_cursor: int, http_client: httpx.Client, start_date: str = "2024-01-01", end_date: str = "2024-12-31") -> dict:
    resp = http_client.get(f"{BIORXIV_DETAILS_URL}/{start_date}/{end_date}/{start_cursor}")
    resp.raise_for_status()
    return resp.json()


def download_biorxiv_pdf(doi: str, http_client: httpx.Client) -> Optional[bytes]:
    pdf_url = f"https://www.biorxiv.org/content/{doi}.full.pdf"
    try:
        resp = http_client.get(pdf_url, follow_redirects=True, timeout=30.0)
        if resp.status_code == 200 and resp.content.startswith(b"%PDF"):
            return resp.content
    except Exception as exc:
        print(f"[biorxiv_connector] PDF download failed for {doi}: {exc}")
    return None


def ingest_biorxiv(
    limit: int,
    raw_pdf_dir: Path,
    manifest_path: Path,
    start_date: str = "2024-01-01",
    end_date: str = "2024-12-31",
) -> list[ManifestRow]:
    raw_pdf_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[ManifestRow] = []
    cursor = 0
    with httpx.Client(timeout=30.0, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}) as client:
        while len(rows) < limit:
            time.sleep(RATE_LIMIT_SECONDS)
            try:
                data = fetch_recent_details(cursor, client, start_date=start_date, end_date=end_date)
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

                doi = entry.get("doi", "")
                pdf_bytes = download_biorxiv_pdf(doi, client)
                if not pdf_bytes:
                    print(f"[biorxiv_connector] skip {doi}: failed to download PDF")
                    continue

                doc_id = doi.replace("/", "_")
                raw_file_path = raw_pdf_dir / f"{doc_id}.pdf"
                raw_file_path.write_bytes(pdf_bytes)

                import re
                entry_date = entry.get("date") or entry.get("version_date") or start_date
                year_match = re.search(r"\b(19\d\d|20\d\d)\b", entry_date)
                pub_year = int(year_match.group(0)) if year_match else None

                row = ManifestRow(
                    doc_id=doc_id,
                    source="biorxiv",
                    license=license_tag,
                    doi=doi,
                    title=entry.get("title", ""),
                    retrieved_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    raw_path=str(raw_file_path),
                    publication_year=pub_year,
                )
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
    parser.add_argument("--start-date", default="2024-01-01")
    parser.add_argument("--end-date", default="2024-12-31")
    args = parser.parse_args()

    result_rows = ingest_biorxiv(
        limit=args.limit,
        raw_pdf_dir=Path("data/raw_pdfs"),
        manifest_path=Path("data/processed/manifest.jsonl"),
        start_date=args.start_date,
        end_date=args.end_date,
    )
    print(f"Ingested {len(result_rows)} documents.")
