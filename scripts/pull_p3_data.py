"""
Phase P3: Bulk pull of UniProtKB and RCSB PDB records for all 18 taxa into staging.
Enforces cursor-based pagination, raw-page disk caching with SHA-256 provenance,
asserts reported vs stored count reconciliation, applies confirmed relevance rules R1-R4,
and explicitly attributes every entry to its specific species while updating taxa registry scope.
"""
from __future__ import annotations

import json
import sqlite3
import time
import hashlib
import random
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "paleo_metadata.db"
RAW_CACHE_ROOT = ROOT / "data" / "raw_cache"
RAW_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
REPORT_FILE = ROOT / "docs" / "verification" / "p3_pull_reconciliation_report.json"

USER_AGENT = "PaleoRAG-DataPuller/1.0 (contact: paleorag@example.edu)"
HEADERS = {"User-Agent": USER_AGENT}

# Project-defined gene panel from README.md:73-95 and scripts/audit_uniprot_accessions.py:MIN_LENGTH_BY_GENE
PROJECT_GENE_PANEL = {
    "HBB", "HBA", "HBA1", "HBA2", "FOXP2", "MC1R", "EPAS1", "TRPV3", "COL1A1", "COL1A2",
    "TBX15", "TBX5", "CYTB", "COX1", "COX2", "COX3", "ND1", "ND2", "ND3", "ND4", "ND4L", "ND5", "ND6",
    "PLA", "CAF1", "YOPM", "HA", "NA", "PB1", "PB2", "PA", "NP", "M1", "M2", "NS1", "NS2"
}

# Scope and query definitions per taxon
TAXON_QUERY_CONFIG = {
    "PRAG-TAX-001": {
        "query": "taxonomy_id:37349",
        "scope_note": "Standard species scope: exact taxon node Mammuthus primigenius.",
        "pdb_tax_id": 37349,
    },
    "PRAG-TAX-002": {
        "query": "taxonomy_id:63221",
        "scope_note": "Standard subspecies scope: exact taxon node Homo sapiens neanderthalensis.",
        "pdb_tax_id": 63221,
    },
    "PRAG-TAX-003": {
        "query": "taxonomy_id:632 AND reviewed:true",
        "scope_note": "Curated reference scope: high-confidence Swiss-Prot reviewed canonical proteome for Yersinia pestis.",
        "pdb_tax_id": 632,
        "pdb_cap": 25,
    },
    "PRAG-TAX-004": {
        "query": "taxonomy_id:2562269",
        "scope_note": "Standard species scope: exact taxon node Aenocyon dirus.",
        "pdb_tax_id": 2562269,
    },
    "PRAG-TAX-005": {
        "query": "taxonomy_id:2770979",
        "scope_note": "Standard species scope: exact taxon node Panthera spelaea.",
        "pdb_tax_id": 2770979,
    },
    "PRAG-TAX-006": {
        "query": "taxonomy_id:268291",
        "scope_note": "Standard species scope: exact taxon node Bison priscus.",
        "pdb_tax_id": 268291,
    },
    "PRAG-TAX-007": {
        "query": "taxonomy_id:741158",
        "scope_note": "Standard subspecies scope: exact taxon node Homo sapiens subsp. 'Denisova'.",
        "pdb_tax_id": 741158,
    },
    "PRAG-TAX-008": {
        "query": "taxonomy_id:9275",
        "scope_note": "Standard species scope: exact taxon node Thylacinus cynocephalus.",
        "pdb_tax_id": 9275,
    },
    "PRAG-TAX-009": {
        "query": "taxonomy_id:222863",
        "scope_note": "Standard species scope: exact taxon node Coelodonta antiquitatis.",
        "pdb_tax_id": 222863,
    },
    "PRAG-TAX-010": {
        "query": "taxonomy_id:13265",
        "scope_note": "Expanded clade scope: includes records across the genus Smilodon (S. fatalis and S. populator).",
        "pdb_tax_id": 13265,
    },
    "PRAG-TAX-011": {
        "query": "taxonomy_id:187135",
        "scope_note": "Standard species scope: exact taxon node Raphus cucullatus.",
        "pdb_tax_id": 187135,
    },
    "PRAG-TAX-012": {
        "query": "taxonomy_id:187118",
        "scope_note": "Standard species scope: exact taxon node Ectopistes migratorius.",
        "pdb_tax_id": 187118,
    },
    "PRAG-TAX-013": {
        "query": "taxonomy_id:48783",
        "scope_note": "Standard genus scope: exact taxon node Mylodon (sloth genus, excluding modern fish taxa).",
        "pdb_tax_id": 48783,
    },
    "PRAG-TAX-014": {
        "query": "taxonomy_id:551196",
        "scope_note": "Standard species scope: exact taxon node Arctodus simus.",
        "pdb_tax_id": 551196,
    },
    "PRAG-TAX-015": {
        "query": "taxonomy_id:11320 AND (strain:\"Brevig Mission\" OR strain:\"South Carolina\" OR reviewed:true)",
        "scope_note": "Targeted historical scope: includes documented 1918 pandemic strains (A/Brevig Mission/1/1918 and A/South Carolina/1/1918) and Swiss-Prot reviewed canonical proteins.",
        "pdb_tax_id": 11320,
        "pdb_search_term": "1918",
        "pdb_cap": 25,
    },
    "PRAG-TAX-016": {
        "query": "(taxonomy_id:1811494 OR taxonomy_id:2546652)",
        "scope_note": "Expanded clade scope: includes records across Glyptodontidae (genera Doedicurus and Glyptodon).",
        "pdb_tax_id": 1811494,
    },
    "PRAG-TAX-017": {
        "query": "taxonomy_id:1563121",
        "scope_note": "Standard genus scope: exact taxon node Toxodon.",
        "pdb_tax_id": 1563121,
    },
    "PRAG-TAX-018": {
        "query": "taxonomy_id:8808",
        "scope_note": "Expanded clade scope: includes records across the order Dinornithiformes (all extinct moa genera: Dinornis, Megalapteryx, Pachyornis, Emeus, Anomalopteryx, Euryapteryx).",
        "pdb_tax_id": 8808,
    },
}

def robust_get(url: str, params: dict | None = None, headers: dict | None = None, timeout: int = 20, max_retries: int = 4) -> requests.Response | None:
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params, headers=headers or HEADERS, timeout=timeout)
            return resp
        except Exception as e:
            if attempt == max_retries:
                print(f"    [WARN] Failed GET {url} after {max_retries} attempts: {e}")
                return None
            time.sleep(1.5 * attempt)
    return None

def init_tables():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")

    # Ensure taxa has included_species and scope_note
    cur.execute("PRAGMA table_info(taxa);")
    cols = [r[1] for r in cur.fetchall()]
    if "included_species" not in cols:
        cur.execute("ALTER TABLE taxa ADD COLUMN included_species TEXT;")
    if "scope_note" not in cols:
        cur.execute("ALTER TABLE taxa ADD COLUMN scope_note TEXT;")

    # Drop and recreate staging tables for clean Phase P3 rebuild
    cur.execute("DROP TABLE IF EXISTS staging_proteins;")
    cur.execute("DROP TABLE IF EXISTS staging_structures;")
    cur.execute("DROP TABLE IF EXISTS rejected_records;")

    cur.execute("""
    CREATE TABLE staging_proteins (
        uniprot_accession TEXT PRIMARY KEY,
        entry_name TEXT NOT NULL,
        reviewed INTEGER NOT NULL,
        protein_name TEXT,
        gene_symbol TEXT,
        ncbi_tax_id INTEGER NOT NULL,
        project_tax_code TEXT NOT NULL,
        organism_tax_id INTEGER NOT NULL,
        organism_name TEXT NOT NULL,
        sequence TEXT NOT NULL,
        sequence_length INTEGER NOT NULL,
        checksum TEXT NOT NULL,
        secondary_accessions TEXT,
        entry_version INTEGER,
        literature_citation_count INTEGER DEFAULT 0,
        has_pdb_xref INTEGER DEFAULT 0,
        pdb_xrefs TEXT,
        relevance_basis TEXT,
        status TEXT NOT NULL,
        source_db TEXT NOT NULL,
        source_record_id TEXT NOT NULL,
        retrieved_at TEXT NOT NULL,
        query_used TEXT NOT NULL,
        raw_response_ref TEXT NOT NULL,
        FOREIGN KEY (ncbi_tax_id) REFERENCES taxa(ncbi_tax_id)
    );
    """)

    cur.execute("""
    CREATE TABLE staging_structures (
        pdb_id TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        chain_ids TEXT,
        method TEXT,
        resolution REAL,
        deposition_date TEXT,
        release_date TEXT,
        source_tax_id INTEGER,
        source_organism_name TEXT,
        title TEXT,
        primary_citation_pmid TEXT,
        primary_citation_doi TEXT,
        mapped_uniprot_accessions TEXT,
        is_obsolete INTEGER DEFAULT 0,
        source_db TEXT NOT NULL,
        source_record_id TEXT NOT NULL,
        retrieved_at TEXT NOT NULL,
        query_used TEXT NOT NULL,
        raw_response_ref TEXT NOT NULL,
        PRIMARY KEY (pdb_id, entity_id)
    );
    """)

    cur.execute("""
    CREATE TABLE rejected_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_type TEXT NOT NULL,
        identifier TEXT NOT NULL,
        reason_code TEXT NOT NULL,
        details TEXT,
        recorded_at TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()

def pull_uniprot_for_taxon(tax_code: str, query: str) -> tuple[int, list[dict], str]:
    """Paginate through all results for a taxon query using UniProt cursor pagination."""
    tax_dir = RAW_CACHE_ROOT / "uniprot" / tax_code
    tax_dir.mkdir(parents=True, exist_ok=True)

    url = "https://rest.uniprot.org/uniprotkb/search"
    params: dict = {"query": query, "format": "json", "size": 500}
    
    all_entries = []
    page_num = 1
    total_reported = 0
    raw_refs = []

    while url:
        time.sleep(0.15)  # polite rate-limiting
        resp = robust_get(url, params=params, timeout=25)
        if resp is None or resp.status_code != 200:
            err_msg = resp.text[:200] if resp else "Connection failed"
            raise RuntimeError(f"UniProt error for {tax_code} page {page_num}: {err_msg}")
        
        if page_num == 1:
            total_reported = int(resp.headers.get("x-total-results", 0))

        page_bytes = resp.content
        sha = hashlib.sha256(page_bytes).hexdigest()
        page_file = tax_dir / f"page_{page_num}_{sha[:8]}.json"
        page_file.write_bytes(page_bytes)
        raw_refs.append(f"{page_file.relative_to(ROOT)}#{sha}")

        page_json = resp.json()
        results = page_json.get("results", [])
        all_entries.extend(results)

        next_url = resp.links.get("next", {}).get("url")
        if next_url:
            url = next_url
            params = {}  # cursor is embedded in next_url
            page_num += 1
        else:
            break

    print(f"  UniProt [{tax_code}]: Reported {total_reported}, Stored {len(all_entries)} in {page_num} page(s)")
    assert len(all_entries) == total_reported, f"Count mismatch for {tax_code}: reported {total_reported} != stored {len(all_entries)}"
    return total_reported, all_entries, ";".join(raw_refs)

def pull_pdb_for_taxon(tax_code: str, tax_id: int, search_term: str | None = None, cap: int | None = None) -> list[dict]:
    """Query RCSB PDB for polymer entities and fetch entity/entry metadata."""
    pdb_dir = RAW_CACHE_ROOT / "pdb" / tax_code
    pdb_dir.mkdir(parents=True, exist_ok=True)

    if search_term:
        search_query = {
            "query": {
                "type": "group",
                "logical_operator": "and",
                "nodes": [
                    {
                        "type": "terminal",
                        "service": "text",
                        "parameters": {
                            "attribute": "rcsb_entity_source_organism.taxonomy_lineage.id",
                            "operator": "exact_match",
                            "value": str(tax_id)
                        }
                    },
                    {
                        "type": "terminal",
                        "service": "text",
                        "parameters": {
                            "attribute": "struct.title",
                            "operator": "contains_words",
                            "value": search_term
                        }
                    }
                ]
            },
            "return_type": "polymer_entity",
            "request_options": {"return_all_hits": True}
        }
    else:
        search_query = {
            "query": {
                "type": "terminal",
                "service": "text",
                "parameters": {
                    "attribute": "rcsb_entity_source_organism.taxonomy_lineage.id",
                    "operator": "exact_match",
                    "value": str(tax_id),
                },
            },
            "return_type": "polymer_entity",
            "request_options": {"return_all_hits": True},
        }

    try:
        s_resp = requests.post("https://search.rcsb.org/rcsbsearch/v2/query", json=search_query, headers=HEADERS, timeout=20)
    except Exception as e:
        print(f"  [WARN] RCSB search failed for {tax_code}: {e}")
        return []

    if s_resp.status_code in (204, 404):
        return []
    if s_resp.status_code != 200:
        return []

    s_bytes = s_resp.content
    s_sha = hashlib.sha256(s_bytes).hexdigest()
    (pdb_dir / f"search_hits_{s_sha[:8]}.json").write_bytes(s_bytes)

    hits = s_resp.json().get("result_set", [])
    if cap and len(hits) > cap:
        print(f"  PDB [{tax_code}]: Found {len(hits)} hits, capping at top {cap} as per optimization plan.")
        hits = hits[:cap]

    entities = []
    for hit in hits:
        identifier = hit["identifier"]  # e.g. "3VRF_1"
        pdb_id, entity_id = identifier.split("_")
        time.sleep(0.1)

        # Check existing cached entity
        cached_pe_files = list(pdb_dir.glob(f"{pdb_id}_{entity_id}_*.json"))
        if cached_pe_files:
            pe_file = cached_pe_files[0]
            pe_bytes = pe_file.read_bytes()
            pe_sha = hashlib.sha256(pe_bytes).hexdigest()
            pe_json = json.loads(pe_bytes.decode("utf-8"))
        else:
            # Fetch polymer entity
            pe_url = f"https://data.rcsb.org/rest/v1/core/polymer_entity/{pdb_id}/{entity_id}"
            pe_resp = robust_get(pe_url, timeout=15)
            if pe_resp is None or pe_resp.status_code != 200:
                continue
            pe_bytes = pe_resp.content
            pe_sha = hashlib.sha256(pe_bytes).hexdigest()
            pe_file = pdb_dir / f"{pdb_id}_{entity_id}_{pe_sha[:8]}.json"
            pe_file.write_bytes(pe_bytes)
            pe_json = pe_resp.json()

        # Check existing cached entry
        entry_file = pdb_dir / f"{pdb_id}_entry.json"
        if entry_file.exists():
            try:
                e_json = json.loads(entry_file.read_text(encoding="utf-8"))
            except Exception:
                e_json = {}
        else:
            e_url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}"
            e_resp = robust_get(e_url, timeout=15)
            if e_resp and e_resp.status_code == 200:
                entry_file.write_bytes(e_resp.content)
                e_json = e_resp.json()
            else:
                e_json = {}

        # Extract fields
        chains = pe_json.get("entity_poly", {}).get("pdbx_strand_id", "").split(",")
        chains = [c.strip() for c in chains if c.strip()]
        method = (e_json.get("exptl", [{}])[0].get("method") or "UNKNOWN")
        resolutions = e_json.get("rcsb_entry_info", {}).get("resolution_combined", [])
        resolution = resolutions[0] if resolutions else None
        dep_date = e_json.get("rcsb_accession_info", {}).get("deposit_date")
        rel_date = e_json.get("rcsb_accession_info", {}).get("initial_release_date")
        title = e_json.get("struct", {}).get("title")
        primary_cit = e_json.get("rcsb_primary_citation", {})
        pmid = str(primary_cit.get("pdbx_database_id_PubMed")) if primary_cit.get("pdbx_database_id_PubMed") else None
        doi = primary_cit.get("pdbx_database_id_DOI")

        # Source organism from entity
        src_orgs = pe_json.get("rcsb_entity_source_organism", [])
        source_org_name = src_orgs[0].get("ncbi_scientific_name") if src_orgs else None

        # UniProt accessions in entity
        u_accs = []
        for ref in pe_json.get("rcsb_polymer_entity_container_identifiers", {}).get("reference_sequence_identifiers", []):
            if ref.get("database_name") == "UniProt":
                u_accs.append(ref.get("database_accession"))

        entities.append({
            "pdb_id": pdb_id,
            "entity_id": entity_id,
            "chain_ids": json.dumps(chains),
            "method": method,
            "resolution": resolution,
            "deposition_date": dep_date,
            "release_date": rel_date,
            "source_tax_id": tax_id,
            "source_organism_name": source_org_name,
            "title": title,
            "primary_citation_pmid": pmid,
            "primary_citation_doi": doi,
            "mapped_uniprot_accessions": json.dumps(u_accs),
            "is_obsolete": 0,
            "source_db": "RCSB PDB REST API",
            "source_record_id": f"{pdb_id}_{entity_id}",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "query_used": f"rcsb_entity_source_organism.taxonomy_lineage.id:{tax_id}",
            "raw_response_ref": f"{pe_file.relative_to(ROOT)}#{pe_sha}",
        })

    print(f"  PDB [{tax_code}]: Retrieved {len(entities)} polymer entities")
    return entities

def evaluate_relevance(rec: dict, has_pdb: bool) -> tuple[str, str]:
    """Evaluate relevance rules R1-R4 for a protein record."""
    if has_pdb:
        return "PDB_MAPPED", "STAGING_ACCEPTED"

    # R1: Reviewed (Swiss-Prot)
    if rec.get("reviewed"):
        return "R1:REVIEWED", "STAGING_ACCEPTED"

    # R2: Has >= 1 literature citation
    if rec.get("literature_citation_count", 0) > 0:
        return "R2:LITERATURE_CITED", "STAGING_ACCEPTED"

    # R3: In Project Gene Panel
    gene = (rec.get("gene_symbol") or "").upper()
    if gene and gene in PROJECT_GENE_PANEL:
        return "R3:PROJECT_PANEL", "STAGING_ACCEPTED"

    # Otherwise STAGING_REJECTED
    return "NOT_RELEVANT", "STAGING_REJECTED"

def main():
    print("=" * 60)
    print("Executing Phase P3: Bulk Pull with Explicit Species Attribution")
    print("=" * 60)

    init_tables()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT tax_id_code, ncbi_tax_id, common_name, scientific_name FROM taxa ORDER BY tax_id_code")
    taxa_rows = cur.fetchall()
    conn.close()

    total_pulled_proteins = 0
    total_pulled_structures = 0
    relevance_counts = {}
    taxon_reconciliation = []
    rejected_sample_pool = []

    for tax_code, tax_id, common_name, sci_name in taxa_rows:
        cfg = TAXON_QUERY_CONFIG[tax_code]
        u_query = cfg["query"]
        scope_note = cfg["scope_note"]
        pdb_tax_id = cfg.get("pdb_tax_id", tax_id)
        pdb_term = cfg.get("pdb_search_term")
        pdb_cap = cfg.get("pdb_cap")

        print(f"\n[{tax_code}] {common_name} (Codified NCBI TaxID: {tax_id})")
        print(f"  Query: {u_query}")
        print(f"  Scope: {scope_note}")

        # 1. Pull UniProt entries
        rep_count, entries, raw_ref_str = pull_uniprot_for_taxon(tax_code, u_query)
        total_pulled_proteins += len(entries)

        # 2. Pull PDB structures
        pdb_entities = pull_pdb_for_taxon(tax_code, pdb_tax_id, search_term=pdb_term, cap=pdb_cap)
        total_pulled_structures += len(pdb_entities)

        # Collect PDB accessions directly mapped by PDB entities
        pdb_mapped_accs = set()
        for pe in pdb_entities:
            for acc in json.loads(pe["mapped_uniprot_accessions"]):
                pdb_mapped_accs.add(acc)

        # 3. Store PDB entities into staging_structures
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON;")

        for pe in pdb_entities:
            cur.execute("""
            INSERT OR REPLACE INTO staging_structures (
                pdb_id, entity_id, chain_ids, method, resolution,
                deposition_date, release_date, source_tax_id, source_organism_name, title,
                primary_citation_pmid, primary_citation_doi, mapped_uniprot_accessions,
                is_obsolete, source_db, source_record_id, retrieved_at, query_used, raw_response_ref
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pe["pdb_id"], pe["entity_id"], pe["chain_ids"], pe["method"], pe["resolution"],
                pe["deposition_date"], pe["release_date"], pe["source_tax_id"], pe["source_organism_name"], pe["title"],
                pe["primary_citation_pmid"], pe["primary_citation_doi"], pe["mapped_uniprot_accessions"],
                pe["is_obsolete"], pe["source_db"], pe["source_record_id"], pe["retrieved_at"], pe["query_used"], pe["raw_response_ref"]
            ))

        # 4. Parse and store UniProt proteins with explicit species attribution
        now_utc = datetime.now(timezone.utc).isoformat()
        taxon_accepted = 0
        taxon_rejected = 0
        distinct_species = set()

        for entry in entries:
            acc = entry["primaryAccession"]
            entry_name = entry.get("uniProtkbId", acc)
            is_reviewed = 1 if entry.get("entryType") == "UniProtKB reviewed (Swiss-Prot)" else 0
            src_db_name = "UniProtKB/Swiss-Prot" if is_reviewed else "UniProtKB/TrEMBL"

            # Organism specifics (exact species/subspecies)
            org_obj = entry.get("organism", {})
            entry_org_tax_id = int(org_obj.get("taxonId", tax_id))
            entry_org_name = org_obj.get("scientificName", sci_name)
            distinct_species.add(entry_org_name)

            # Protein & Gene Names
            desc = entry.get("proteinDescription", {})
            rec_name = desc.get("recommendedName", {}).get("fullName", {}).get("value")
            sub_name = desc.get("submissionNames", [{}])[0].get("fullName", {}).get("value") if desc.get("submissionNames") else None
            prot_name = rec_name or sub_name or "Uncharacterized protein"

            genes = entry.get("genes", [])
            gene_symbol = genes[0].get("geneName", {}).get("value") if genes and "geneName" in genes[0] else None

            # Sequence
            seq_obj = entry.get("sequence", {})
            sequence = seq_obj.get("value", "")
            seq_len = seq_obj.get("length", len(sequence))
            crc64 = seq_obj.get("crc64", "")

            # Secondary accessions & version
            sec_accs = entry.get("secondaryAccessions", [])
            version = entry.get("entryAudit", {}).get("entryVersion", 1)

            # Citations
            citations = entry.get("references", [])
            cit_count = len(citations)

            # PDB cross-references
            pdb_xrefs = [
                x["id"] for x in entry.get("uniProtKBCrossReferences", [])
                if x.get("database") == "PDB"
            ]
            has_pdb = 1 if (pdb_xrefs or acc in pdb_mapped_accs) else 0

            # Relevance rule evaluation
            rec_dict = {
                "reviewed": is_reviewed,
                "literature_citation_count": cit_count,
                "gene_symbol": gene_symbol,
            }
            rel_basis, status = evaluate_relevance(rec_dict, bool(has_pdb))

            relevance_counts[rel_basis] = relevance_counts.get(rel_basis, 0) + 1
            if status == "STAGING_ACCEPTED":
                taxon_accepted += 1
            else:
                taxon_rejected += 1
                rejected_sample_pool.append({
                    "accession": acc,
                    "entry_name": entry_name,
                    "protein_name": prot_name,
                    "gene_symbol": gene_symbol,
                    "taxon_code": tax_code,
                    "taxon_common": common_name,
                    "organism_name": entry_org_name,
                    "organism_tax_id": entry_org_tax_id,
                    "reason_code": "NOT_RELEVANT",
                })

            cur.execute("""
            INSERT OR REPLACE INTO staging_proteins (
                uniprot_accession, entry_name, reviewed, protein_name, gene_symbol,
                ncbi_tax_id, project_tax_code, organism_tax_id, organism_name,
                sequence, sequence_length, checksum, secondary_accessions,
                entry_version, literature_citation_count, has_pdb_xref, pdb_xrefs,
                relevance_basis, status, source_db, source_record_id, retrieved_at, query_used, raw_response_ref
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                acc, entry_name, is_reviewed, prot_name, gene_symbol,
                tax_id, tax_code, entry_org_tax_id, entry_org_name,
                sequence, seq_len, crc64, json.dumps(sec_accs),
                version, cit_count, has_pdb, json.dumps(pdb_xrefs),
                rel_basis, status, src_db_name, acc, now_utc, u_query, raw_ref_str
            ))

        # 5. Update taxa table with represented species and scope note
        sorted_species = sorted(list(distinct_species)) if distinct_species else [sci_name]
        cur.execute("""
        UPDATE taxa
        SET included_species = ?, scope_note = ?
        WHERE tax_id_code = ?
        """, (json.dumps(sorted_species), scope_note, tax_code))

        conn.commit()
        conn.close()

        taxon_reconciliation.append({
            "tax_id_code": tax_code,
            "taxon_common": common_name,
            "codified_ncbi_tax_id": tax_id,
            "query_used": u_query,
            "scope_note": scope_note,
            "represented_species_count": len(sorted_species),
            "represented_species": sorted_species,
            "reported_uniprot_total": rep_count,
            "stored_uniprot_total": len(entries),
            "reconciled": rep_count == len(entries),
            "pdb_entities_stored": len(pdb_entities),
            "accepted_proteins": taxon_accepted,
            "rejected_proteins": taxon_rejected,
        })

    # Record rejected pool into rejected_records table
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")
    for rj in rejected_sample_pool:
        cur.execute("""
        INSERT INTO rejected_records (entity_type, identifier, reason_code, details, recorded_at)
        VALUES (?, ?, ?, ?, ?)
        """, (
            "protein", rj["accession"], rj["reason_code"],
            f"[{rj['taxon_code']}] {rj['taxon_common']} - {rj['organism_name']} (NCBI:{rj['organism_tax_id']}) - {rj['protein_name']} (Gene: {rj['gene_symbol']})",
            datetime.now(timezone.utc).isoformat()
        ))
    conn.commit()
    conn.close()

    # Draw 20 random rejected records for human review (seed=42)
    rng = random.Random(42)
    sample_20_rejected = rng.sample(rejected_sample_pool, min(20, len(rejected_sample_pool)))

    report_payload = {
        "metadata": {
            "date": datetime.now(timezone.utc).isoformat(),
            "phase": "P3",
            "total_proteins_pulled": total_pulled_proteins,
            "total_structures_pulled": total_pulled_structures,
            "relevance_distribution": relevance_counts,
        },
        "taxon_reconciliation": taxon_reconciliation,
        "sample_20_rejected_records": sample_20_rejected,
    }

    REPORT_FILE.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")
    print(f"\n==========================================")
    print(f"Phase P3 Complete!")
    print(f"Total Stored Proteins: {total_pulled_proteins}")
    print(f"Total Stored Polymer Entities: {total_pulled_structures}")
    print(f"Relevance Counts: {relevance_counts}")
    print(f"Reconciliation Report written to {REPORT_FILE}")
    print(f"==========================================")

if __name__ == "__main__":
    main()
