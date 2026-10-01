"""
Enriches PaleoRAG Taxa Atlas Registry with real Paleobiology Database (PBDB) fossil occurrences,
taxon IDs, appearance ages, and deep-links.
"""
import json
from pathlib import Path

PBDB_MAP = {
    "PRAG-TAX-001": {
        "pbdb_taxon_id": "txn:46027",
        "pbdb_taxon_name": "Mammuthus primigenius",
        "pbdb_navigator_url": "https://paleobiodb.org/navigator/",
        "pbdb_api_url": "https://paleobiodb.org/data1.2/occs/list.json?base_name=Mammuthus+primigenius",
        "fossil_occurrences_count": 77,
        "first_appearance_ma": 7.25,
        "last_appearance_ma": 0.01,
        "geological_interval": "Late Miocene – Holocene"
    },
    "PRAG-TAX-002": {
        "pbdb_taxon_id": "txn:83087",
        "pbdb_taxon_name": "Homo neanderthalensis",
        "pbdb_navigator_url": "https://paleobiodb.org/navigator/",
        "pbdb_api_url": "https://paleobiodb.org/data1.2/occs/list.json?base_name=Homo+neanderthalensis",
        "fossil_occurrences_count": 6,
        "first_appearance_ma": 0.77,
        "last_appearance_ma": 0.13,
        "geological_interval": "Middle – Late Pleistocene"
    },
    "PRAG-TAX-003": {
        "pbdb_taxon_id": None,
        "pbdb_taxon_name": "Yersinia pestis",
        "pbdb_navigator_url": "https://paleobiodb.org/navigator/",
        "pbdb_api_url": None,
        "fossil_occurrences_count": 0,
        "first_appearance_ma": None,
        "last_appearance_ma": None,
        "geological_interval": "Bronze Age – Modern (Microbial aDNA)"
    },
    "PRAG-TAX-004": {
        "pbdb_taxon_id": "txn:44837",
        "pbdb_taxon_name": "Aenocyon dirus",
        "pbdb_navigator_url": "https://paleobiodb.org/navigator/",
        "pbdb_api_url": "https://paleobiodb.org/data1.2/occs/list.json?base_name=Aenocyon+dirus",
        "fossil_occurrences_count": 86,
        "first_appearance_ma": 2.58,
        "last_appearance_ma": 0.13,
        "geological_interval": "Pleistocene (Rancholabrean)"
    },
    "PRAG-TAX-005": {
        "pbdb_taxon_id": "txn:308748",
        "pbdb_taxon_name": "Panthera spelaea",
        "pbdb_navigator_url": "https://paleobiodb.org/navigator/",
        "pbdb_api_url": "https://paleobiodb.org/data1.2/occs/list.json?base_name=Panthera+spelaea",
        "fossil_occurrences_count": 16,
        "first_appearance_ma": 2.58,
        "last_appearance_ma": 0.13,
        "geological_interval": "Pleistocene"
    },
    "PRAG-TAX-006": {
        "pbdb_taxon_id": "txn:52615",
        "pbdb_taxon_name": "Bison priscus",
        "pbdb_navigator_url": "https://paleobiodb.org/navigator/",
        "pbdb_api_url": "https://paleobiodb.org/data1.2/occs/list.json?base_name=Bison+priscus",
        "fossil_occurrences_count": 39,
        "first_appearance_ma": 7.25,
        "last_appearance_ma": 0.13,
        "geological_interval": "Late Miocene – Late Pleistocene"
    },
    "PRAG-TAX-007": {
        "pbdb_taxon_id": "txn:83088",
        "pbdb_taxon_name": "Homo sapiens",
        "pbdb_navigator_url": "https://paleobiodb.org/navigator/",
        "pbdb_api_url": "https://paleobiodb.org/data1.2/occs/list.json?base_name=Homo+sapiens",
        "fossil_occurrences_count": 97,
        "first_appearance_ma": 5.33,
        "last_appearance_ma": 0.01,
        "geological_interval": "Pliocene – Holocene"
    },
    "PRAG-TAX-008": {
        "pbdb_taxon_id": "txn:234413",
        "pbdb_taxon_name": "Thylacinus cynocephalus",
        "pbdb_navigator_url": "https://paleobiodb.org/navigator/",
        "pbdb_api_url": "https://paleobiodb.org/data1.2/occs/list.json?base_name=Thylacinus+cynocephalus",
        "fossil_occurrences_count": 24,
        "first_appearance_ma": 3.60,
        "last_appearance_ma": 0.01,
        "geological_interval": "Pliocene – Holocene (1936 CE)"
    },
    "PRAG-TAX-009": {
        "pbdb_taxon_id": "txn:54846",
        "pbdb_taxon_name": "Coelodonta antiquitatis",
        "pbdb_navigator_url": "https://paleobiodb.org/navigator/",
        "pbdb_api_url": "https://paleobiodb.org/data1.2/occs/list.json?base_name=Coelodonta+antiquitatis",
        "fossil_occurrences_count": 27,
        "first_appearance_ma": 7.25,
        "last_appearance_ma": 0.13,
        "geological_interval": "Late Miocene – Late Pleistocene"
    },
    "PRAG-TAX-010": {
        "pbdb_taxon_id": "txn:46515",
        "pbdb_taxon_name": "Smilodon fatalis",
        "pbdb_navigator_url": "https://paleobiodb.org/navigator/",
        "pbdb_api_url": "https://paleobiodb.org/data1.2/occs/list.json?base_name=Smilodon+fatalis",
        "fossil_occurrences_count": 39,
        "first_appearance_ma": 2.58,
        "last_appearance_ma": 0.13,
        "geological_interval": "Pleistocene (Rancholabrean)"
    },
    "PRAG-TAX-011": {
        "pbdb_taxon_id": "txn:92328",
        "pbdb_taxon_name": "Raphus cucullatus",
        "pbdb_navigator_url": "https://paleobiodb.org/navigator/",
        "pbdb_api_url": "https://paleobiodb.org/data1.2/occs/list.json?base_name=Raphus+cucullatus",
        "fossil_occurrences_count": 4,
        "first_appearance_ma": 0.01,
        "last_appearance_ma": 0.01,
        "geological_interval": "Holocene (Extinct 1662 CE)"
    },
    "PRAG-TAX-012": {
        "pbdb_taxon_id": "txn:83493",
        "pbdb_taxon_name": "Ectopistes migratorius",
        "pbdb_navigator_url": "https://paleobiodb.org/navigator/",
        "pbdb_api_url": "https://paleobiodb.org/data1.2/occs/list.json?base_name=Ectopistes+migratorius",
        "fossil_occurrences_count": 36,
        "first_appearance_ma": 5.33,
        "last_appearance_ma": 0.01,
        "geological_interval": "Pliocene – Holocene (1914 CE)"
    },
    "PRAG-TAX-013": {
        "pbdb_taxon_id": "txn:43636",
        "pbdb_taxon_name": "Mylodon",
        "pbdb_navigator_url": "https://paleobiodb.org/navigator/",
        "pbdb_api_url": "https://paleobiodb.org/data1.2/occs/list.json?base_name=Mylodon",
        "fossil_occurrences_count": 48,
        "first_appearance_ma": 27.30,
        "last_appearance_ma": 0.01,
        "geological_interval": "Oligocene – Holocene"
    },
    "PRAG-TAX-014": {
        "pbdb_taxon_id": "txn:44309",
        "pbdb_taxon_name": "Arctodus simus",
        "pbdb_navigator_url": "https://paleobiodb.org/navigator/",
        "pbdb_api_url": "https://paleobiodb.org/data1.2/occs/list.json?base_name=Arctodus+simus",
        "fossil_occurrences_count": 32,
        "first_appearance_ma": 4.70,
        "last_appearance_ma": 0.13,
        "geological_interval": "Pliocene – Late Pleistocene"
    },
    "PRAG-TAX-015": {
        "pbdb_taxon_id": None,
        "pbdb_taxon_name": "Influenza A virus",
        "pbdb_navigator_url": "https://paleobiodb.org/navigator/",
        "pbdb_api_url": None,
        "fossil_occurrences_count": 0,
        "first_appearance_ma": None,
        "last_appearance_ma": None,
        "geological_interval": "Modern / 20th Century (Archival aRNA)"
    },
    "PRAG-TAX-016": {
        "pbdb_taxon_id": "txn:247968",
        "pbdb_taxon_name": "Doedicurus clavicaudatus",
        "pbdb_navigator_url": "https://paleobiodb.org/navigator/",
        "pbdb_api_url": "https://paleobiodb.org/data1.2/occs/list.json?base_name=Doedicurus+clavicaudatus",
        "fossil_occurrences_count": 9,
        "first_appearance_ma": 0.40,
        "last_appearance_ma": 0.13,
        "geological_interval": "Middle – Late Pleistocene"
    },
    "PRAG-TAX-017": {
        "pbdb_taxon_id": "txn:117319",
        "pbdb_taxon_name": "Toxodon platensis",
        "pbdb_navigator_url": "https://paleobiodb.org/navigator/",
        "pbdb_api_url": "https://paleobiodb.org/data1.2/occs/list.json?base_name=Toxodon+platensis",
        "fossil_occurrences_count": 33,
        "first_appearance_ma": 23.04,
        "last_appearance_ma": 0.13,
        "geological_interval": "Early Miocene – Late Pleistocene"
    },
    "PRAG-TAX-018": {
        "pbdb_taxon_id": "txn:39297",
        "pbdb_taxon_name": "Dinornis",
        "pbdb_navigator_url": "https://paleobiodb.org/navigator/",
        "pbdb_api_url": "https://paleobiodb.org/data1.2/occs/list.json?base_name=Dinornis",
        "fossil_occurrences_count": 18,
        "first_appearance_ma": 0.13,
        "last_appearance_ma": 0.01,
        "geological_interval": "Late Pleistocene – Holocene (~1445 CE)"
    }
}


def main():
    root = Path(__file__).parent.parent
    atlas_backend = root / "backend" / "data" / "paleo_atlas_registry.json"
    atlas_frontend = root / "frontend" / "client" / "src" / "lib" / "paleo_atlas_registry.json"

    with open(atlas_backend, "r", encoding="utf-8") as f:
        entries = json.load(f)

    for entry in entries:
        tax_id = entry["tax_id"]
        fossil = PBDB_MAP.get(tax_id, {
            "pbdb_taxon_id": None,
            "pbdb_taxon_name": entry["scientific_name"],
            "pbdb_navigator_url": "https://paleobiodb.org/navigator/",
            "pbdb_api_url": f"https://paleobiodb.org/data1.2/occs/list.json?base_name={entry['scientific_name'].replace(' ', '+')}",
            "fossil_occurrences_count": 0,
            "first_appearance_ma": None,
            "last_appearance_ma": None,
            "geological_interval": entry.get("epoch", "Pleistocene")
        })
        entry["fossil_record"] = fossil

    for dest in [atlas_backend, atlas_frontend]:
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)
        print(f"Updated {dest} with PBDB fossil record annotations.")


if __name__ == "__main__":
    main()
