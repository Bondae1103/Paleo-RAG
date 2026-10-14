import sqlite3

conn = sqlite3.connect("data/paleo_metadata.db")
cur = conn.cursor()

cur.execute("SELECT count(*) FROM protein_structure_mappings")
print("Total mappings in DB:", cur.fetchone()[0])

cur.execute("SELECT project_tax_code, count(DISTINCT uniprot_accession), count(DISTINCT pdb_id), count(*) FROM protein_structure_mappings GROUP BY project_tax_code")
print("Mappings by taxon (TaxCode, Proteins, PDBs, Links):")
for r in cur.fetchall():
    print(" ", r)

cur.execute("SELECT taxon_match_status, count(*) FROM protein_structure_mappings GROUP BY taxon_match_status")
print("Taxon match status:")
for r in cur.fetchall():
    print(" ", r)

cur.execute("SELECT mapping_source, count(*) FROM protein_structure_mappings GROUP BY mapping_source")
print("Mapping source:")
for r in cur.fetchall():
    print(" ", r)

print("\nMammoth mappings:")
cur.execute("SELECT uniprot_accession, pdb_id, chain_id, entity_id, uniprot_start, uniprot_end, pdb_start, pdb_end, mapping_source, taxon_match_status FROM protein_structure_mappings WHERE project_tax_code = 'PRAG-TAX-001'")
for r in cur.fetchall():
    print(" ", r)

print("\nNeanderthal mappings:")
cur.execute("SELECT uniprot_accession, pdb_id, chain_id, entity_id, uniprot_start, uniprot_end, pdb_start, pdb_end, mapping_source, taxon_match_status FROM protein_structure_mappings WHERE project_tax_code = 'PRAG-TAX-002'")
for r in cur.fetchall():
    print(" ", r)
