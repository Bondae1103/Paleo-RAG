"""
Enriches paleo_atlas_registry.json in both backend and frontend with
the validated included_species and scope_note from data/paleo_metadata.db.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "paleo_metadata.db"
BACKEND_ATLAS = ROOT / "backend" / "data" / "paleo_atlas_registry.json"
FRONTEND_ATLAS = ROOT / "frontend" / "client" / "src" / "lib" / "paleo_atlas_registry.json"

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT tax_id_code, included_species, scope_note FROM taxa")
    taxa_map = {
        row[0]: {
            "included_species": json.loads(row[1]) if row[1] else [],
            "scope_note": row[2] or "",
        }
        for row in cur.fetchall()
    }
    conn.close()

    for atlas_path in [BACKEND_ATLAS, FRONTEND_ATLAS]:
        if not atlas_path.exists():
            print(f"File not found: {atlas_path}")
            continue
        data = json.loads(atlas_path.read_text(encoding="utf-8"))
        for entry in data:
            code = entry.get("tax_id")
            if code in taxa_map:
                entry["included_species"] = taxa_map[code]["included_species"]
                entry["scope_note"] = taxa_map[code]["scope_note"]
        atlas_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"Updated {atlas_path} with included_species and scope_note.")

if __name__ == "__main__":
    main()
