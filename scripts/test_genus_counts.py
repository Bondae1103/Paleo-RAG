import requests

headers = {'User-Agent': 'PaleoRAG-Auditor/1.0 (contact: paleorag@example.edu)'}

genera = [
    ('Mammuthus', 'Mammuthus primigenius'),
    ('Smilodon', 'Smilodon fatalis'),
    ('Coelodonta', 'Coelodonta antiquitatis'),
    ('Mylodon', 'Mylodon darwinii'),
    ('Dinornis', 'Dinornis robustus'),
    ('Thylacinus', 'Thylacinus cynocephalus'),
    ('Ectopistes', 'Ectopistes migratorius'),
    ('Raphus', 'Raphus cucullatus'),
    ('Arctodus', 'Arctodus simus'),
    ('Doedicurus', 'Doedicurus clavicaudatus'),
    ('Aenocyon', 'Aenocyon dirus'),
    ('Toxodon', 'Toxodon')
]

for genus, sp in genera:
    r_sp = requests.get(f'https://rest.uniprot.org/uniprotkb/search?query=taxonomy_name:"{sp}"&size=0', headers=headers, timeout=10)
    cnt_sp = r_sp.headers.get('x-total-results', '0')
    r_gen = requests.get(f'https://rest.uniprot.org/uniprotkb/search?query=taxonomy_name:{genus}&size=0', headers=headers, timeout=10)
    cnt_gen = r_gen.headers.get('x-total-results', '0')
    print(f'{genus} -> species "{sp}": {cnt_sp} | genus "{genus}": {cnt_gen}')
