import requests

headers = {'User-Agent': 'PaleoRAG-Auditor/1.0 (contact: paleorag@example.edu)'}

for term in ['Smilodon', 'Smilodon fatalis', 'Smilodon populator']:
    url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=taxonomy&term={term}&retmode=json'
    r = requests.get(url, headers=headers, timeout=10)
    ids = r.json().get('esearchresult', {}).get('idlist', [])
    print(f'NCBI {term}: {ids}')

queries = [
    'taxonomy_id:13266',
    'taxonomy_name:"Smilodon fatalis"',
    'taxonomy_name:"Smilodon populator"',
    'taxonomy_name:Smilodon',
    'Smilodon'
]

for q in queries:
    url = f'https://rest.uniprot.org/uniprotkb/search?query={q}&size=5&format=json'
    r = requests.get(url, headers=headers, timeout=10)
    cnt = r.headers.get('x-total-results')
    print(f'UniProt {q} -> count: {cnt}')
    if r.status_code == 200:
        for rec in r.json().get('results', []):
            acc = rec.get('primaryAccession')
            org = rec.get('organism', {}).get('scientificName')
            taxid = rec.get('organism', {}).get('taxonId')
            desc = rec.get('proteinDescription', {}).get('recommendedName', {}).get('fullName', {}).get('value')
            print(f'   -> {acc} | {org} (TaxID: {taxid}) | {desc}')
