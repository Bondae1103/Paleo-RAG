"""
Quantify legacy data errors for Phase P0 baseline.
Random sample of 100 legacy protein records (seed=42) verified live against
authoritative UniProtKB and RCSB PDB APIs.
Results written to docs/verification/legacy_error_audit_sample100_seed42.json.
"""
from __future__ import annotations

import json
import random
import time
import hashlib
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_FILE = ROOT / "backend" / "data" / "paleo_atlas_registry.json"
CACHE_DIR = ROOT / "data" / "bio_cache" / "audit_p0"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = ROOT / "docs" / "verification" / "legacy_error_audit_sample100_seed42.json"

USER_AGENT = "PaleoRAG-Auditor/1.0 (contact: paleorag@example.edu)"
HEADERS = {"User-Agent": USER_AGENT}

def fetch_cached(url: str) -> tuple[int, dict | None, str]:
    url_hash = hashlib.sha256(url.encode()).hexdigest()
    cache_path = CACHE_DIR / f"{url_hash}.json"
    if cache_path.exists():
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        return data["status_code"], data["json"], data["sha256"]
    
    time.sleep(0.1)  # rate limit safety
    try:
        res = requests.get(url, headers=HEADERS, timeout=12)
        status_code = res.status_code
        content = res.content
        res_sha = hashlib.sha256(content).hexdigest()
        res_json = res.json() if status_code == 200 else None
        cache_path.write_text(
            json.dumps({"status_code": status_code, "json": res_json, "sha256": res_sha}, indent=2),
            encoding="utf-8"
        )
        return status_code, res_json, res_sha
    except Exception as e:
        return 500, {"error": str(e)}, ""

def main():
    reg = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    all_sites = []
    
    for t in reg:
        tax_id = t["tax_id"]
        sci_name = t["scientific_name"]
        common_name = t["common_name"]
        
        # 1. target locus extinct
        tl = t.get("target_locus", {})
        all_sites.append({
            "site_id": f"{tax_id}:target_locus:extinct",
            "taxon_id": tax_id,
            "taxon_common": common_name,
            "expected_organism": sci_name,
            "is_extinct": True,
            "gene_symbol": tl.get("gene_symbol"),
            "protein_name": tl.get("protein_name"),
            "uniprot_acc": tl.get("extinct_uniprot_acc"),
            "pdb_id": t.get("structure", {}).get("pdb_id"),
        })
        
        # 2. target locus extant counterpart
        ec = t.get("extant_counterpart", {})
        all_sites.append({
            "site_id": f"{tax_id}:target_locus:extant",
            "taxon_id": tax_id,
            "taxon_common": common_name,
            "expected_organism": ec.get("scientific_name"),
            "is_extinct": False,
            "gene_symbol": tl.get("gene_symbol"),
            "protein_name": tl.get("protein_name"),
            "uniprot_acc": ec.get("extant_uniprot_acc"),
            "pdb_id": None,
        })
        
        # 3. molecular samples
        for idx, s in enumerate(t.get("molecular_samples", [])):
            sec = s.get("extant_counterpart", {})
            all_sites.append({
                "site_id": f"{tax_id}:sample_{idx}:extinct",
                "taxon_id": tax_id,
                "taxon_common": common_name,
                "expected_organism": sci_name,
                "is_extinct": True,
                "gene_symbol": s.get("gene_symbol"),
                "protein_name": s.get("protein_name"),
                "uniprot_acc": s.get("extinct_uniprot_acc"),
                "pdb_id": s.get("structure", {}).get("pdb_id") if s.get("structure") else None,
            })
            all_sites.append({
                "site_id": f"{tax_id}:sample_{idx}:extant",
                "taxon_id": tax_id,
                "taxon_common": common_name,
                "expected_organism": sec.get("scientific_name"),
                "is_extinct": False,
                "gene_symbol": s.get("gene_symbol"),
                "protein_name": s.get("protein_name"),
                "uniprot_acc": sec.get("extant_uniprot_acc"),
                "pdb_id": None,
            })
            
    print(f"Total legacy protein sites enumerated: {len(all_sites)}")
    
    # Random sample of 100 with seed=42
    rng = random.Random(42)
    sample = rng.sample(all_sites, 100)
    print(f"Drawn random sample of {len(sample)} records with seed=42.")
    
    results = []
    summary_counts = {
        "total_sampled": len(sample),
        "uniprot_null": 0,
        "uniprot_resolved_200": 0,
        "uniprot_not_found_404": 0,
        "uniprot_taxon_match_exact": 0,
        "uniprot_taxon_mismatch": 0,
        "pdb_id_present": 0,
        "pdb_resolved_200": 0,
        "pdb_not_found_404": 0,
        "pdb_taxon_match": 0,
        "pdb_taxon_mismatch": 0,
        "pdb_contains_target_uniprot": 0,
        "pdb_lacks_target_uniprot": 0,
    }
    
    for idx, rec in enumerate(sample):
        acc = rec.get("uniprot_acc")
        pdb_id = rec.get("pdb_id")
        exp_org = rec.get("expected_organism")
        
        entry_result = {
            "index": idx,
            "site_id": rec["site_id"],
            "taxon_id": rec["taxon_id"],
            "expected_organism": exp_org,
            "gene_symbol": rec["gene_symbol"],
            "uniprot_acc": acc,
            "pdb_id": pdb_id,
            "uniprot_audit": {},
            "pdb_audit": {},
            "error_flags": [],
        }
        
        # 1. Check UniProt
        if not acc:
            summary_counts["uniprot_null"] += 1
            entry_result["uniprot_audit"]["verdict"] = "NULL_ACCESSION"
            entry_result["error_flags"].append("UNIPROT_ACCESSION_NULL")
        else:
            u_status, u_json, u_sha = fetch_cached(f"https://rest.uniprot.org/uniprotkb/{acc}.json")
            if u_status == 200 and u_json:
                summary_counts["uniprot_resolved_200"] += 1
                live_org = u_json.get("organism", {}).get("scientificName", "")
                live_taxid = u_json.get("organism", {}).get("taxonId")
                live_genes = [g.get("geneName", {}).get("value") for g in u_json.get("genes", []) if "geneName" in g]
                
                entry_result["uniprot_audit"] = {
                    "status_code": 200,
                    "live_organism": live_org,
                    "live_taxon_id": live_taxid,
                    "live_genes": live_genes,
                    "sha256": u_sha,
                }
                
                # Compare organism
                clean_exp = exp_org.split("(")[0].strip() if exp_org else ""
                clean_live = live_org.split("(")[0].strip()
                if clean_exp.lower() in clean_live.lower() or clean_live.lower() in clean_exp.lower():
                    summary_counts["uniprot_taxon_match_exact"] += 1
                    entry_result["uniprot_audit"]["taxon_match"] = True
                else:
                    summary_counts["uniprot_taxon_mismatch"] += 1
                    entry_result["uniprot_audit"]["taxon_match"] = False
                    entry_result["error_flags"].append("UNIPROT_ORGANISM_MISMATCH")
            else:
                summary_counts["uniprot_not_found_404"] += 1
                entry_result["uniprot_audit"] = {"status_code": u_status, "verdict": "NOT_FOUND"}
                entry_result["error_flags"].append("UNIPROT_ACCESSION_NOT_FOUND")
                
        # 2. Check PDB
        if pdb_id:
            summary_counts["pdb_id_present"] += 1
            p_status, p_json, p_sha = fetch_cached(f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}")
            if p_status == 200 and p_json:
                summary_counts["pdb_resolved_200"] += 1
                struct_title = p_json.get("struct", {}).get("title", "")
                polymer_ids = p_json.get("rcsb_entry_container_identifiers", {}).get("polymer_entity_ids", ["1"])
                
                # Fetch entity 1 info
                pe_status, pe_json, pe_sha = fetch_cached(f"https://data.rcsb.org/rest/v1/core/polymer_entity/{pdb_id}/{polymer_ids[0]}")
                entity_orgs = []
                entity_uniprots = []
                if pe_status == 200 and pe_json:
                    for src in pe_json.get("rcsb_entity_source_organism", []):
                        if src.get("scientific_name"):
                            entity_orgs.append(src["scientific_name"])
                    for ref in pe_json.get("rcsb_polymer_entity_container_identifiers", {}).get("reference_sequence_identifiers", []):
                        if ref.get("database_name") == "UniProt":
                            entity_uniprots.append(ref.get("database_accession"))
                            
                entry_result["pdb_audit"] = {
                    "status_code": 200,
                    "title": struct_title,
                    "polymer_entity_organisms": entity_orgs,
                    "polymer_entity_uniprots": entity_uniprots,
                    "sha256": p_sha,
                }
                
                # Compare PDB organism with expected
                pdb_matched_org = False
                clean_exp = exp_org.split("(")[0].strip() if exp_org else ""
                for e_org in entity_orgs:
                    if clean_exp.lower() in e_org.lower() or e_org.lower() in clean_exp.lower():
                        pdb_matched_org = True
                        break
                        
                if pdb_matched_org:
                    summary_counts["pdb_taxon_match"] += 1
                    entry_result["pdb_audit"]["taxon_match"] = True
                else:
                    summary_counts["pdb_taxon_mismatch"] += 1
                    entry_result["pdb_audit"]["taxon_match"] = False
                    entry_result["error_flags"].append("PDB_ORGANISM_MISMATCH")
                    
                # Does PDB contain the claimed UniProt accession?
                if acc and acc in entity_uniprots:
                    summary_counts["pdb_contains_target_uniprot"] += 1
                    entry_result["pdb_audit"]["contains_uniprot"] = True
                else:
                    summary_counts["pdb_lacks_target_uniprot"] += 1
                    entry_result["pdb_audit"]["contains_uniprot"] = False
                    if acc:
                        entry_result["error_flags"].append("PDB_DOES_NOT_CONTAIN_CLAIMED_UNIPROT")
            else:
                summary_counts["pdb_not_found_404"] += 1
                entry_result["pdb_audit"] = {"status_code": p_status, "verdict": "NOT_FOUND"}
                entry_result["error_flags"].append("PDB_ENTRY_NOT_FOUND")
                
        results.append(entry_result)
        if (idx + 1) % 10 == 0:
            print(f"Audited {idx + 1}/100 records...")
            
    final_output = {
        "metadata": {
            "audit_date": "2026-10-13",
            "seed": 42,
            "sample_size": 100,
            "total_population": len(all_sites),
            "sources": ["UniProt REST API (rest.uniprot.org)", "RCSB PDB REST API (data.rcsb.org)"]
        },
        "summary": summary_counts,
        "records": results
    }
    
    OUT_FILE.write_text(json.dumps(final_output, indent=2), encoding="utf-8")
    print(f"\nAudit complete! Results saved to {OUT_FILE}")
    print("\nSummary Counts:")
    for k, v in summary_counts.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
