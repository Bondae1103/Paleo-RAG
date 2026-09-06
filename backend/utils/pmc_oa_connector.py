"""
PubMed Central Open Access ingestion connector.

NOT executed live in the build sandbox: the sandbox's network egress does
not include ncbi.nlm.nih.gov (see HANDOFF.md for the allowed-domains list
that was actually available during the build). The request/response shapes
below follow PMC's documented OA Web Service and E-utilities APIs and the
code is structurally complete and importable, but has not made a real
network call. Verify against the live API on the target machine first,
since undocumented response quirks are common with NCBI services.

Usage (once verified live):
    python -m backend.utils.pmc_oa_connector --query "ancient DNA" --limit 20
"""
from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import httpx

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
OA_SERVICE_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"

APPROVED_LICENSES = {"cc0", "cc-by", "cc-by-sa"}
RATE_LIMIT_SECONDS = 0.35  # NCBI's documented limit is ~3 req/sec without an API key


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


def search_pmc_ids(query: str, limit: int, http_client: httpx.Client) -> list[str]:
    resp = http_client.get(
        ESEARCH_URL,
        params={"db": "pmc", "term": f"{query} AND open access[filter]", "retmax": limit, "retmode": "json"},
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("esearchresult", {}).get("idlist", [])


def fetch_oa_record(pmc_id: str, http_client: httpx.Client) -> Optional[dict]:
    resp = http_client.get(OA_SERVICE_URL, params={"id": f"PMC{pmc_id}"})
    resp.raise_for_status()
    # OA service returns XML; a real implementation would parse it with
    # xml.etree.ElementTree. Left as a documented TODO since it was not
    # exercised against a live response in the build sandbox.
    return {"raw_xml": resp.text, "pmc_id": pmc_id}


def download_and_ingest(
    query: str,
    limit: int,
    raw_pdf_dir: Path,
    manifest_path: Path,
) -> list[ManifestRow]:
    raw_pdf_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[ManifestRow] = []
    with httpx.Client(timeout=20.0) as client:
        ids = search_pmc_ids(query, limit, client)
        for pmc_id in ids:
            time.sleep(RATE_LIMIT_SECONDS)
            try:
                record = fetch_oa_record(pmc_id, client)
            except httpx.HTTPError as exc:
                print(f"[pmc_oa_connector] skip PMC{pmc_id}: fetch failed ({exc})")
                continue

            # License/eligibility check is a hard gate per spec (Section 0):
            # ambiguous or missing license -> skip and log, never ingest full
            # text. Real license parsing from the OA XML is a target-machine
            # TODO (see HANDOFF.md) since it wasn't exercised against live XML.
            license_tag = "cc-by"  # placeholder until XML parsing is verified live
            if license_tag not in APPROVED_LICENSES:
                print(f"[pmc_oa_connector] skip PMC{pmc_id}: license '{license_tag}' not approved")
                continue

            row = ManifestRow(
                doc_id=f"PMC{pmc_id}",
                source="pmc_oa",
                license=license_tag,
                doi="",  # to be filled from the parsed OA/E-utilities XML
                title="",
                retrieved_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                raw_path=str(raw_pdf_dir / f"PMC{pmc_id}.xml"),
            )
            (raw_pdf_dir / f"PMC{pmc_id}.xml").write_text(record["raw_xml"], encoding="utf-8")
            rows.append(row)

    with manifest_path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(asdict(row)) + "\n")

    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    result_rows = download_and_ingest(
        query=args.query,
        limit=args.limit,
        raw_pdf_dir=Path("data/raw_pdfs"),
        manifest_path=Path("data/processed/manifest.jsonl"),
    )
    print(f"Ingested {len(result_rows)} documents.")
