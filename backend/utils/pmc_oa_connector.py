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
ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

APPROVED_LICENSES = {"cc0", "cc-by", "cc-by-sa", "cc-by-nc", "cc-by-nc-sa", "cc-by-4.0", "cc-by-3.0"}
RATE_LIMIT_SECONDS = 0.35  # NCBI limit is ~3 req/sec without API key


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


def search_pmc_ids(query: str, limit: int, http_client: httpx.Client) -> list[str]:
    resp = http_client.get(
        ESEARCH_URL,
        params={"db": "pmc", "term": f"{query} AND open access[filter]", "retmax": limit, "retmode": "json"},
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("esearchresult", {}).get("idlist", [])


def fetch_pmc_summary(pmc_id: str, http_client: httpx.Client) -> dict:
    try:
        resp = http_client.get(
            ESUMMARY_URL,
            params={"db": "pmc", "id": pmc_id, "retmode": "json"},
        )
        resp.raise_for_status()
        data = resp.json()
        item = data.get("result", {}).get(pmc_id, {})
        title = item.get("title", "")
        doi = ""
        for aid in item.get("articleids", []):
            if aid.get("idtype") == "doi":
                doi = aid.get("value", "")
                break
        pubdate = item.get("pubdate") or item.get("epubdate") or item.get("sortdate") or item.get("sortpubdate") or ""
        import re
        year_match = re.search(r"\b(19\d\d|20\d\d)\b", str(pubdate))
        pub_year = int(year_match.group(0)) if year_match else None
        return {"title": title, "doi": doi, "pubdate": str(pubdate), "publication_year": pub_year}
    except Exception:
        return {"title": "", "doi": "", "pubdate": "", "publication_year": None}


def extract_license_from_xml(xml_text: str) -> Optional[str]:
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return None

    # Search for license elements or xlink:href in permissions
    for lic in root.findall(".//permissions//license"):
        # Check license-type attribute
        lic_type = lic.attrib.get("license-type", "").lower()
        if "open-access" in lic_type or "cc" in lic_type:
            pass
        # Check xlink:href or text
        for k, v in lic.attrib.items():
            if "href" in k.lower():
                v_lower = v.lower()
                if "zero" in v_lower or "cc0" in v_lower:
                    return "cc0"
                if "by-sa" in v_lower:
                    return "cc-by-sa"
                if "by-nc" in v_lower:
                    return "cc-by-nc"
                if "by" in v_lower or "creativecommons.org/licenses/by" in v_lower:
                    return "cc-by"

        lic_text = "".join(lic.itertext()).lower()
        if "creative commons attribution" in lic_text or "cc by" in lic_text:
            return "cc-by"
        if "public domain" in lic_text or "cc0" in lic_text:
            return "cc0"
        if "commercial" in lic_text and "attribution" in lic_text:
            return "cc-by-nc"

    # Default check for open-access indicator
    for custom_meta in root.findall(".//custom-meta"):
        txt = "".join(custom_meta.itertext()).lower()
        if "open-access" in txt:
            return "cc-by"

    return None


def fetch_pmc_xml(pmc_id: str, http_client: httpx.Client) -> Optional[str]:
    resp = http_client.get(
        EFETCH_URL,
        params={"db": "pmc", "id": pmc_id, "retmode": "xml"},
    )
    resp.raise_for_status()
    return resp.text


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
                xml_text = fetch_pmc_xml(pmc_id, client)
                if not xml_text:
                    continue
            except httpx.HTTPError as exc:
                print(f"[pmc_oa_connector] skip PMC{pmc_id}: fetch failed ({exc})")
                continue

            license_tag = extract_license_from_xml(xml_text)
            if not license_tag or license_tag not in APPROVED_LICENSES:
                print(f"[pmc_oa_connector] skip PMC{pmc_id}: license '{license_tag}' not approved/found")
                continue

            summary = fetch_pmc_summary(pmc_id, client)

            row = ManifestRow(
                doc_id=f"PMC{pmc_id}",
                source="pmc_oa",
                license=license_tag,
                doi=summary.get("doi", ""),
                title=summary.get("title", ""),
                retrieved_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                raw_path=str(raw_pdf_dir / f"PMC{pmc_id}.xml"),
            )
            (raw_pdf_dir / f"PMC{pmc_id}.xml").write_text(xml_text, encoding="utf-8")
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
