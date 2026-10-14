import requests

headers = {'User-Agent': 'PaleoRAG/1.0'}

def check_q(q):
    r = requests.get('https://rest.uniprot.org/uniprotkb/search', params={'query': q, 'format': 'json', 'size': 10}, headers=headers)
    tot = r.headers.get('x-total-results', len(r.json().get('results', [])))
    print(f'Query: {q} -> Total: {tot}')
    for res in r.json().get('results', []):
        acc = res.get('primaryAccession')
        org = res.get('organism', {}).get('scientificName')
        tid = res.get('organism', {}).get('taxonId')
        pname = res.get('proteinDescription', {}).get('recommendedName', {}).get('fullName', {}).get('value') or 'Uncharacterized'
        print(f'   {acc} | {tid} ({org}) | {pname}')

print('--- DIRE WOLF ---')
check_q('Aenocyon')
check_q('taxonomy_name:Aenocyon')
check_q('Canis dirus')
check_q('taxonomy_name:"Canis dirus"')

print('--- SHORT FACED BEAR ---')
check_q('Arctodus')
check_q('taxonomy_name:Arctodus')
check_q('taxonomy_id:551195')

print('--- DODO ---')
check_q('taxonomy_id:187135') # Raphus cucullatus
check_q('Raphus')

print('--- TOXODON ---')
check_q('taxonomy_id:1563121')
check_q('Toxodon')
