import sqlite3
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CH_DIR = ROOT / "data" / "changelogs"
CH_DIR.mkdir(parents=True, exist_ok=True)
CH_LOG = CH_DIR / "p3_pull_changelog.jsonl"

conn = sqlite3.connect(ROOT / "data" / "paleo_metadata.db")
cur = conn.cursor()

cur.execute("""
    SELECT uniprot_accession, entry_name, reviewed, organism_name, organism_tax_id, project_tax_code, sequence_length, query_used, raw_response_ref
    FROM staging_proteins
""")
rows = cur.fetchall()

entries = []
for idx, r in enumerate(rows, start=1):
    entry = {
        "#": idx,
        "Type": "add",
        "Target": f"staging_proteins:{r[0]}",
        "Before": "—",
        "After": f"{r[1]} ({r[3]} [NCBI:{r[4]}], {r[6]} aa, reviewed={bool(r[2])})",
        "Reason": f"Bulk pull for {r[5]} with explicit species attribution",
        "Evidence": r[8].split(";")[0],
        "Verified by": f"Query: {r[7]}"
    }
    entries.append(entry)

with open(CH_LOG, "w", encoding="utf-8") as f:
    for e in entries:
        f.write(json.dumps(e) + "\n")

print(f"Wrote {len(entries)} changelog entries to {CH_LOG}")

# Sample 10 random entries with seed 42
rng = random.Random(42)
sample10 = rng.sample(entries, 10)
print("\nSample 10 (seed 42):")
for s in sample10:
    print(f"| {s['#']} | {s['Type']} | {s['Target']} | {s['Before']} | {s['After']} | {s['Reason']} | {s['Evidence']} | {s['Verified by']} |")
