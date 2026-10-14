"""
Phase P1/P3.1 Count-Only Probe Script.
Measures real result counts from UniProtKB (reviewed, unreviewed, total)
and RCSB PDB (entries, polymer entities) for all 18 taxa without bulk downloading.
Outputs docs/verification/p3_count_probe_measured.json.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_FILE = ROOT / "docs" / "verification" / "p3_count_probe_measured.json"

USER_AGENT = "PaleoRAG-Auditor/1.0 (contact: paleorag@example.edu)"
HEADERS = {"User-Agent": USER_AGENT}

TAXA = [
    {"common": "Woolly Mammoth", "name": "Mammuthus primigenius", "tax_id": "37349"},
    {"common": "Neanderthal", "name": "Homo sapiens neanderthalensis", "tax_id": "63221"},
    {"common": "Ancient Yersinia pestis", "name": "Yersinia pestis", "tax_id": "632"},
    {"common": "Dire Wolf", "name": "Aenocyon dirus", "tax_id": "2562269"},
    {"common": "Cave Lion", "name": "Panthera spelaea", "tax_id": "2770979"},
    {"common": "Steppe Bison", "name": "Bison priscus", "tax_id": "268291"},
    {"common": "Denisovan", "name": "Homo sapiens subsp. Denisova", "tax_id": "741158"},
    {"common": "Tasmanian Tiger", "name": "Thylacinus cynocephalus", "tax_id": "9275"},
    {"common": "Woolly Rhinoceros", "name": "Coelodonta antiquitatis", "tax_id": "222863"},
    {"common": "Saber-Toothed Cat", "name": "Smilodon fatalis", "tax_id": "13266"},
    {"common": "Dodo", "name": "Raphus cucullatus", "tax_id": "187135"},
    {"common": "Passenger Pigeon", "name": "Ectopistes migratorius", "tax_id": "187118"},
    {"common": "Darwin's Ground Sloth", "name": "Mylodon darwinii", "tax_id": "48784"},
    {"common": "Giant Short-Faced Bear", "name": "Arctodus simus", "tax_id": "551196"},
    {"common": "1918 Spanish Flu Virus", "name": "Influenza A virus", "tax_id": "11320"},
    {"common": "Giant Glyptodont", "name": "Doedicurus clavicaudatus", "tax_id": "1811495"},
    {"common": "Toxodon", "name": "Toxodon", "tax_id": "1563121"},
    {"common": "South Island Giant Moa", "name": "Dinornis robustus", "tax_id": "314500"},
]

def main():
    probe_results = []
    print("Starting measured count probe across all 18 taxa...")

    for t in TAXA:
        tid = t["tax_id"]
        time.sleep(0.2)  # polite rate-limiting

        # 1. UniProt Total
        u_all = requests.get(
            f"https://rest.uniprot.org/uniprotkb/search?query=taxonomy_id:{tid}&size=0",
            headers=HEADERS,
            timeout=15,
        )
        tot = int(u_all.headers.get("x-total-results", 0)) if u_all.status_code == 200 else -1

        # 2. UniProt Reviewed (Swiss-Prot)
        time.sleep(0.1)
        u_rev = requests.get(
            f"https://rest.uniprot.org/uniprotkb/search?query=taxonomy_id:{tid} AND reviewed:true&size=0",
            headers=HEADERS,
            timeout=15,
        )
        rev = int(u_rev.headers.get("x-total-results", 0)) if u_rev.status_code == 200 else -1

        # 3. UniProt Unreviewed (TrEMBL)
        unrev = tot - rev if tot >= 0 and rev >= 0 else -1

        # 4. PDB Search (Entries)
        time.sleep(0.1)
        q_entry = {
            "query": {
                "type": "terminal",
                "service": "text",
                "parameters": {
                    "attribute": "rcsb_entity_source_organism.taxonomy_lineage.id",
                    "operator": "exact_match",
                    "value": tid,
                },
            },
            "return_type": "entry",
            "request_options": {"paginate": {"start": 0, "rows": 0}},
        }
        p_e = requests.post("https://search.rcsb.org/rcsbsearch/v2/query", json=q_entry, headers=HEADERS, timeout=15)
        pdb_entries = p_e.json().get("total_count", 0) if p_e.status_code == 200 else 0

        # 5. PDB Search (Polymer Entities)
        time.sleep(0.1)
        q_poly = {
            "query": {
                "type": "terminal",
                "service": "text",
                "parameters": {
                    "attribute": "rcsb_entity_source_organism.taxonomy_lineage.id",
                    "operator": "exact_match",
                    "value": tid,
                },
            },
            "return_type": "polymer_entity",
            "request_options": {"paginate": {"start": 0, "rows": 0}},
        }
        p_p = requests.post("https://search.rcsb.org/rcsbsearch/v2/query", json=q_poly, headers=HEADERS, timeout=15)
        pdb_polymers = p_p.json().get("total_count", 0) if p_p.status_code == 200 else 0

        res_row = {
            "taxon_name": t["name"],
            "common_name": t["common"],
            "ncbi_tax_id": tid,
            "uniprot_reviewed": rev,
            "uniprot_unreviewed": unrev,
            "uniprot_total": tot,
            "pdb_entries": pdb_entries,
            "pdb_polymer_entities": pdb_polymers,
        }
        probe_results.append(res_row)
        print(f"[{t['common']}] tax_id={tid} -> UniProt: {tot} (rev: {rev}, unrev: {unrev}) | PDB: {pdb_entries} entries, {pdb_polymers} entities")

    OUT_FILE.write_text(json.dumps(probe_results, indent=2), encoding="utf-8")
    print(f"\nCount probe complete! Results saved to {OUT_FILE}")

if __name__ == "__main__":
    main()
