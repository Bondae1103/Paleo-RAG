"""
Read-only audit of every `genomics` block in the PaleoDB Atlas Registry
(`target_locus`-level and every `molecular_samples[]` entry) against the live
Ensembl REST API.

For each genomics block this:
  - Resolves the expected Ensembl species slug from that same block's own
    `extant_counterpart.scientific_name` (the only organism whose genome
    Ensembl could plausibly host, since the extinct taxon itself never has
    an Ensembl entry) -- never from the registry's existing (possibly wrong)
    `ensembl_species` value, so a stale cross-organism mismatch is itself
    detected rather than assumed correct.
  - Checks that resolved slug against Ensembl's live /info/species list.
  - If valid, calls /lookup/symbol/<species>/<gene_symbol> and records the
    live chromosome/start/end/assembly.
  - Never invents a substitute species. If the expected species has no
    Ensembl entry, or the gene symbol isn't found for it, the site is
    reported unresolved -- not silently pointed at a different organism's
    genome.

Usage:
    python -m scripts.audit_ensembl_loci                # audit only
    python -m scripts.audit_ensembl_loci --apply         # audit + write
                                                          # live-verified
                                                          # coordinates, or
                                                          # null out
                                                          # unresolved ones
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
ENSEMBL_BASE = "https://rest.ensembl.org"

# Binomial -> Ensembl REST species slug, for cases where Ensembl only hosts a
# named subspecies/breed-reference assembly of the registry's stated extant
# organism (verified against the live /info/species list; never a different
# species).
SPECIES_SLUG_OVERRIDES: dict[str, str] = {
    "Canis lupus": "canis_lupus_familiaris",
    "Bison bison": "bison_bison_bison",
}


def slugify(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def load_species_list(client: httpx.Client) -> set[str]:
    for attempt in range(5):
        try:
            r = client.get(f"{ENSEMBL_BASE}/info/species", params={"content-type": "application/json"})
            if r.status_code == 200:
                return {s["name"] for s in r.json().get("species", [])}
        except Exception:
            pass
        time.sleep(2.0 * (attempt + 1))
    raise RuntimeError("Could not load Ensembl species list after retries.")


def iter_genomics_sites(entry: dict):
    """Yield (path, container, gene_symbol, extant_organism, tax_id) for every
    genomics block in one taxon entry."""
    tax_id = entry["tax_id"]
    tl = entry.get("target_locus", {})
    g = entry.get("genomics")
    if g is not None:
        yield (f"{tax_id}.genomics", g, tl.get("gene_symbol"), entry.get("extant_counterpart", {}).get("scientific_name"), tax_id)
    for s in entry.get("molecular_samples", []):
        sg = s.get("genomics")
        if sg is not None:
            sid = s.get("sample_id")
            yield (f"{tax_id}.molecular_samples[{sid}].genomics", sg, s.get("gene_symbol"), s.get("extant_counterpart", {}).get("scientific_name"), tax_id)


_gene_cache: dict[tuple[str, str], dict | None] = {}


def fetch_gene(client: httpx.Client, species_slug: str, gene_symbol: str) -> dict | None:
    """Live Ensembl lookup, memoized per (species, gene) pair -- many registry
    sites across different taxa/samples share the same pair (e.g. every
    CYTB sample for a given extant species), so this avoids re-fetching the
    same live record dozens of times."""
    cache_key = (species_slug, gene_symbol)
    if cache_key in _gene_cache:
        return _gene_cache[cache_key]

    url = f"{ENSEMBL_BASE}/lookup/symbol/{species_slug}/{gene_symbol}"
    last_status = None
    result = None
    # Ensembl REST has been observed taking 10-15s per response under load;
    # a short per-attempt timeout here just manufactures false "not found"
    # verdicts for genes that do exist. Patience, not aggressive retrying,
    # is what this endpoint needs.
    for attempt in range(4):
        try:
            r = client.get(url, params={"content-type": "application/json"}, timeout=40.0)
        except Exception as exc:
            last_status = f"exception:{exc}"
            time.sleep(3.0)
            continue
        last_status = r.status_code
        if r.status_code == 200:
            result = r.json()
            break
        if r.status_code in (400, 404):
            # Genuinely no such gene symbol for this species (Ensembl returns
            # 400 for an unrecognized symbol as often as a clean 404) -- not
            # transient, no point retrying.
            result = None
            break
        retry_after = float(r.headers.get("Retry-After", 3.0 * (attempt + 1)))
        time.sleep(min(retry_after, 10.0))
    else:
        print(f"    (gave up on {species_slug}/{gene_symbol} after retries, last_status={last_status})", flush=True)

    time.sleep(1.0)
    _gene_cache[cache_key] = result
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    with open(REGISTRY_PATHS[0], "r", encoding="utf-8") as f:
        registry = json.load(f)

    client = httpx.Client(timeout=40.0, headers={"User-Agent": "PaleoRAG-audit/1.0 (mukilkrish04@gmail.com)"})
    now = datetime.now(timezone.utc).isoformat()

    valid_species = load_species_list(client)
    print(f"Loaded {len(valid_species)} valid Ensembl species slugs.\n")

    records = []
    for entry in registry:
        for path, g, gene, extant_org, tax_id in iter_genomics_sites(entry):
            registry_species = g.get("ensembl_species")
            expected_slug = SPECIES_SLUG_OVERRIDES.get(extant_org, slugify(extant_org) if extant_org else None)

            rec = {
                "path": path,
                "tax_id": tax_id,
                "gene": gene,
                "extant_organism": extant_org,
                "registry_ensembl_species": registry_species,
                "expected_slug": expected_slug,
                "registry_chrom": g.get("chromosome"),
                "registry_start": g.get("start"),
                "registry_end": g.get("end"),
                "registry_assembly": g.get("assembly"),
            }

            if not expected_slug:
                rec["verdict"] = "no_extant_organism"
                records.append(rec)
                print(f"[{'no_extant_organism':24s}] {path}")
                continue

            if expected_slug not in valid_species:
                rec["verdict"] = "species_not_in_ensembl"
                records.append(rec)
                print(f"[{'species_not_in_ensembl':24s}] {path:55s} expected={expected_slug}")
                continue

            gene_data = fetch_gene(client, expected_slug, gene) if gene else None
            if not gene_data:
                rec["verdict"] = "gene_not_found"
                records.append(rec)
                print(f"[{'gene_not_found':24s}] {path:55s} species={expected_slug} gene={gene}")
                continue

            live_chrom = str(gene_data.get("seq_region_name", ""))
            live_chrom_norm = live_chrom if live_chrom.startswith("chr") else f"chr{live_chrom}"
            rec.update(
                verdict="resolved",
                species_matches=(registry_species == expected_slug or (registry_species or "").lower() == expected_slug),
                live_chromosome=live_chrom_norm,
                live_start=gene_data.get("start"),
                live_end=gene_data.get("end"),
                live_assembly=gene_data.get("assembly_name"),
                live_gene_id=gene_data.get("id"),
                live_strand=gene_data.get("strand"),
            )
            records.append(rec)
            print(
                f"[{'resolved':24s}] {path:55s} species={expected_slug} gene={gene} "
                f"live={live_chrom_norm}:{gene_data.get('start')}-{gene_data.get('end')} ({gene_data.get('assembly_name')}) "
                f"registry_species_match={rec['species_matches']}"
            )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"ensembl_locus_audit_{now[:10]}.json"
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
    unresolved = 0
    for entry in registry:
        for path, g, gene, extant_org, tax_id in iter_genomics_sites(entry):
            match = next((r for r in records if r["path"] == path), None)
            if not match:
                continue
            v = match["verdict"]
            if v == "resolved":
                g["ensembl_species"] = match["expected_slug"]
                g["chromosome"] = match["live_chromosome"]
                g["start"] = match["live_start"]
                g["end"] = match["live_end"]
                g["assembly"] = match["live_assembly"]
                g["ensembl_gene_id"] = match["live_gene_id"]
                g["ensembl_validation"] = {
                    "status": "verified_live",
                    "evidence_source": f"https://rest.ensembl.org/lookup/symbol/{match['expected_slug']}/{gene}",
                    "validated_at": now,
                    "note": None,
                }
                corrected += 1
            else:
                g["ensembl_species"] = None
                g["chromosome"] = None
                g["start"] = None
                g["end"] = None
                g["assembly"] = None
                g["ensembl_validation"] = {
                    "status": "unverified",
                    "evidence_source": None,
                    "validated_at": now,
                    "note": f"verdict={v}; no live-verified Ensembl gene record exists for the organism this locus claims ({extant_org!r}). Coordinates nulled rather than left pointing at a stale or wrong-organism locus.",
                }
                unresolved += 1

    for p in REGISTRY_PATHS:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)
        print(f"Wrote corrected registry: {p}")
    print(f"\nLive-verified & corrected: {corrected}  Unresolved (nulled): {unresolved}")


if __name__ == "__main__":
    main()
