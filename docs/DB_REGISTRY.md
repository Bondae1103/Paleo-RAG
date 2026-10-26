# DB_REGISTRY.md — Authoritative Database API Registry

Before invoking any external database service, official documentation is verified and an empirical live test call is recorded here per Prime Directive 3.

---

## 1. UniProtKB REST API
- **Official Documentation**: https://www.uniprot.org/help/api
- **Base URL**: `https://rest.uniprot.org`
- **Key Endpoints**:
  - Entry lookup: `GET /uniprotkb/{accession}.json`
  - Search / Query: `GET /uniprotkb/search?query={query}&format=json&size={size}`
- **ID Format (Regex)**: `^[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$`
- **License / Terms**: Creative Commons Attribution (CC BY 4.0)
- **Rate Limit Policy**: Polite client etiquette: <= 3–5 requests/sec with descriptive `User-Agent`. Respect HTTP 429 Retry-After.
- **Link Template**: `https://www.uniprot.org/uniprotkb/{accession}/entry`
- **Empirical Test Call**:
  - Request: `GET https://rest.uniprot.org/uniprotkb/D3U1H9.json`
  - User-Agent: `PaleoRAG-Auditor/1.0 (contact: paleorag@example.edu)`
  - Status: `200 OK`
  - Observed Response Fields: `organism.scientificName` ("Mammuthus primigenius"), `organism.taxonId` (37349), `entryType` ("UniProtKB reviewed (Swiss-Prot)"), `genes` (`[{'geneName': {'value': 'D'}}]`).

---

## 2. RCSB Protein Data Bank (PDB) REST API
- **Official Documentation**: https://data.rcsb.org
- **Base URL**: `https://data.rcsb.org/rest/v1`
- **Key Endpoints**:
  - Entry Core Data: `GET /core/entry/{entry_id}`
  - Polymer Entity Core Data: `GET /core/polymer_entity/{entry_id}/{entity_id}`
  - Polymer Instance (Chain) Data: `GET /core/polymer_entity_instance/{entry_id}/{asym_id}`
- **ID Format (Regex)**: `^[0-9][A-Za-z0-9]{3}$` (4-character alphanumeric starting with a digit)
- **License / Terms**: CC0 1.0 Universal (public domain)
- **Rate Limit Policy**: No strict commercial cap, but requires standard backoff on 429/5xx and disk caching.
- **Link Template**: `https://www.rcsb.org/structure/{pdb_id}`
- **Empirical Test Call**:
  - Request: `GET https://data.rcsb.org/rest/v1/core/entry/3VRF`
  - Status: `200 OK`
  - Observed Response Fields: `struct.title` ("The crystal structure of hemoglobin from woolly mammoth in the carbonmonoxy forms"), `exptl[0].method` ("X-RAY DIFFRACTION"), `rcsb_entry_info.resolution_combined[0]` (1.55).
  - Entity Request: `GET https://data.rcsb.org/rest/v1/core/polymer_entity/3VRF/1`
  - Status: `200 OK`
  - Observed Response Fields: `rcsb_entity_source_organism[0].scientific_name` ("Mammuthus primigenius"), `rcsb_entity_source_organism[0].ncbi_taxonomy_id` (37349), `rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers` (`UniProt: D3U1H8`).

---

## 3. NCBI Taxonomy API (E-utilities)
- **Official Documentation**: https://www.ncbi.nlm.nih.gov/books/NBK25501/
- **Base URL**: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils`
- **Key Endpoints**:
  - Search: `GET /esearch.fcgi?db=taxonomy&term={term}&retmode=json`
  - Summary: `GET /esummary.fcgi?db=taxonomy&id={tax_id}&retmode=json`
- **ID Format (Regex)**: `^[0-9]+$` (positive integer)
- **License / Terms**: US Government Public Domain / Open Data
- **Rate Limit Policy**: Max 3 requests/sec without API key, or up to 10/sec with key. Polite User-Agent and email required.
- **Link Template**: `https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id={tax_id}`
- **Empirical Test Call**:
  - Request: `GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=taxonomy&id=37349&retmode=json`
  - Status: `200 OK`
  - Observed Response Fields: `result.37349.scientificname` ("Mammuthus primigenius"), `result.37349.rank` ("species"), `result.37349.division` ("placentals").

---

## 4. Paleobiology Database (PBDB) Data Service API
- **Official Documentation**: https://paleobiodb.org/data1.2/
- **Base URL**: `https://paleobiodb.org/data1.2`
- **Key Endpoints**:
  - Single Taxon by Name: `GET /taxa/single.json?name={name}&show=attr`
  - Single Taxon by ID: `GET /taxa/single.json?id={id}&show=attr`
  - Occurrences by Base Name: `GET /occs/list.json?base_name={name}`
- **ID Format (Regex)**: `^(txn:)?[0-9]+$`
- **License / Terms**: Creative Commons CC-BY 4.0
- **Rate Limit Policy**: Standard academic courtesy. Backoff on 429/5xx, disk cache on client.
- **Link Template**: `https://paleobiodb.org/classic/checkTaxonInfo?taxon_no={taxon_no}`
- **Empirical Test Call**:
  - Request: `GET https://paleobiodb.org/data1.2/taxa/single.json?name=Mammuthus%20primigenius&show=attr`
  - Status: `200 OK`
  - Observed Response Fields: `records[0].oid` ("txn:46027"), `records[0].nam` ("Mammuthus primigenius"), `records[0].rnk` (3).
  - Reverse Lookup Request: `GET https://paleobiodb.org/data1.2/taxa/single.json?id=txn:46027&show=attr`
  - Status: `200 OK`
---

## 5. PDBe SIFTS REST API (Structure Integration with Function, Taxonomy and Sequence)
- **Official Documentation**: https://www.ebi.ac.uk/pdbe/api/doc/sifts.html
- **Base URL**: `https://www.ebi.ac.uk/pdbe/api`
- **Key Endpoints**:
  - All Isoforms Mapping: `GET /mappings/all_isoforms/{accession}`
  - Best Structures: `GET /mappings/best_structures/{accession}`
  - UniProt Segments by PDB: `GET /mappings/uniprot_segments/{pdb_id}`
- **ID Format (Regex)**: UniProt Accession regex (`^[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$`)
- **License / Terms**: EMBL-EBI Terms of Use (Open Access for research)
- **Rate Limit Policy**: Max 15 requests/second with polite client etiquette and descriptive User-Agent.
- **Link Template**: `https://www.ebi.ac.uk/pdbe/entry/pdb/{pdb_id}`
- **Empirical Test Call**:
  - Request: `GET https://www.ebi.ac.uk/pdbe/api/mappings/all_isoforms/D3U1H8`
  - Status: `200 OK`
  - Observed Response Fields: `D3U1H8.PDB.3vrf` (`[{'entity_id': 1, 'chain_id': 'A', 'unp_start': 2, 'unp_end': 142, 'start': {'author_residue_number': 1, 'residue_number': 1}, 'end': {'author_residue_number': 141, 'residue_number': 141}}]`).

---

## 6. KEGG REST API (Kyoto Encyclopedia of Genes and Genomes)
- **Official Documentation**: https://www.kegg.jp/kegg/rest/keggapi.html
- **Base URL**: `https://rest.kegg.jp`
- **Key Endpoints**:
  - Info: `GET /info/{database}`
  - Entry Retrieval: `GET /get/{dbentry}`
  - Link Mapping: `GET /link/{target_db}/{source_db}`
- **ID Format (Regex)**: `^(map|ko|ec)?[0-9]{5}$|^[a-z]{3,4}:[0-9A-Za-z_-]+$`
- **License / Terms**: Freely accessible for academic, non-commercial research. Commercial licensing required for commercial redistribution of bulk database files.
- **Rate Limit Policy**: Max 3 requests/sec with polite backoff on 429.
- **Link Template**: `https://www.kegg.jp/entry/{identifier}`
- **Empirical Test Call**:
  - Request: `GET https://rest.kegg.jp/info/pathway`
  - Status: `200 OK`
  - Observed Response Content: `pathway    Kyoto Encyclopedia of Genes and Genomes\nkegg       Release 112.0+/10-13, Oct 26`

---

## 7. InterPro & Pfam REST API
- **Official Documentation**: https://www.ebi.ac.uk/interpro/api/
- **Base URL**: `https://www.ebi.ac.uk/interpro/api`
- **Key Endpoints**:
  - Protein Annotations: `GET /protein/uniprot/{accession}`
  - InterPro Entry: `GET /entry/interpro/{entry_acc}`
  - Pfam Entry: `GET /entry/pfam/{pfam_acc}`
- **ID Format (Regex)**: InterPro: `^IPR[0-9]{6}$` | Pfam: `^PF[0-9]{5}$`
- **License / Terms**: CC0 1.0 Universal (Open Data)
- **Rate Limit Policy**: Up to 15 requests/sec with polite User-Agent.
- **Link Templates**:
  - InterPro: `https://www.ebi.ac.uk/interpro/entry/InterPro/{identifier}`
  - Pfam: `https://www.ebi.ac.uk/interpro/entry/pfam/{identifier}`
- **Empirical Test Call**:
  - Request: `GET https://www.ebi.ac.uk/interpro/api/protein/uniprot/D3U1H8`
  - Status: `200 OK`
  - Observed Response Fields: `metadata.accession` ("D3U1H8"), `entries` (contains "IPR000971" Globin, "PF00042").

---

## 8. NCBI Entrez Gene & RefSeq APIs
- **Official Documentation**: https://www.ncbi.nlm.nih.gov/books/NBK25501/
- **Base URL**: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils`
- **Key Endpoints**:
  - Gene Summary: `GET /esummary.fcgi?db=gene&id={gene_id}&retmode=json`
  - Nuccore Fetch: `GET /efetch.fcgi?db=nuccore&id={acc}&retmode=text&rettype=fasta`
- **ID Format (Regex)**: GeneID: `^[0-9]+$` | RefSeq: `^[A-Z]{2}_[0-9]+(\.[0-9]+)?$`
- **License / Terms**: US Government Public Domain
- **Rate Limit Policy**: 3 requests/sec without API key.
- **Link Templates**:
  - GeneID: `https://www.ncbi.nlm.nih.gov/gene/{identifier}`
  - RefSeq: `https://www.ncbi.nlm.nih.gov/nuccore/{identifier}`
- **Empirical Test Call**:
  - Request: `GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=gene&id=7037&retmode=json`
  - Status: `200 OK`
  - Observed Response Fields: `result.7037.name` ("TFRC").

---

## 9. AlphaFold Protein Structure Database API
- **Official Documentation**: https://alphafold.ebi.ac.uk/api-docs
- **Base URL**: `https://alphafold.ebi.ac.uk/api`
- **Key Endpoints**:
  - Prediction by Accession: `GET /prediction/{accession}`
- **ID Format (Regex)**: `^AF-[A-Z0-9]+-F[0-9]+$`
- **License / Terms**: Creative Commons Attribution (CC-BY 4.0)
- **Rate Limit Policy**: Max 10 requests/sec.
- **Link Template**: `https://alphafold.ebi.ac.uk/entry/{identifier}`
- **Empirical Test Call**:
  - Request: `GET https://alphafold.ebi.ac.uk/api/prediction/D3U1H8`
  - Status: `200 OK`
  - Observed Response Fields: `entryId` ("AF-D3U1H8-F1"), `pdbUrl`, `cifUrl`, `bcifUrl`, `globalMetricValue` (pLDDT: 97.4).

---

## 10. CATH Protein Structure Classification Database
- **Official Documentation**: https://www.cathdb.info/wiki/help:api
- **Base URL**: `https://www.cathdb.info`
- **Key Endpoints**:
  - Superfamily: `GET /version/v4_3_0/api/rest/superfamily/{superfamily_id}`
- **ID Format (Regex)**: `^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$`
- **License / Terms**: CC-BY 4.0
- **Rate Limit Policy**: Standard academic etiquette.
- **Link Template**: `https://www.cathdb.info/version/latest/superfamily/{identifier}`

---

## 11. NCBI PubMed Database API (E-utilities)
- **Official Documentation**: https://www.ncbi.nlm.nih.gov/books/NBK25501/
- **Base URL**: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils`
- **Key Endpoints**:
  - Search: `GET /esearch.fcgi?db=pubmed&term={term}&retmode=json`
  - Summary: `GET /esummary.fcgi?db=pubmed&id={pmids}&retmode=json`
  - Fetch (XML): `GET /efetch.fcgi?db=pubmed&id={pmids}&retmode=xml`
- **ID Format (Regex)**: `^[0-9]{1,9}$` (PMID)
- **License / Terms**: Public Domain / NLM Open Data
- **Rate Limit Policy**: Max 3 requests/sec without API key, up to 10/sec with key. Descriptive User-Agent.
- **Link Template**: `https://pubmed.ncbi.nlm.nih.gov/{identifier}/`
- **Empirical Test Call**:
  - Request: `GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=20448178&retmode=json`
  - Status: `200 OK`
  - Observed Response Fields: `result.20448178.title` ("A draft sequence of the Neandertal genome."), `result.20448178.pubdate` ("2010 May 7"), `result.20448178.articleids` (contains DOI `10.1126/science.1188021` and PMC `PMC5100745`).

---

## 12. Europe PMC REST API
- **Official Documentation**: https://europepmc.org/RestfulWebService
- **Base URL**: `https://www.ebi.ac.uk/europepmc/webservices/rest`
- **Key Endpoints**:
  - Search: `GET /search?query={query}&format=json&resultType=core`
  - Article XML: `GET /article/PMC/{pmcid}/fullTextXML`
- **ID Format (Regex)**: PMID: `^[0-9]{1,9}$` | PMCID: `^PMC[0-9]{4,9}$`
- **License / Terms**: CC0 / Open Access for core API, with article texts subject to respective publisher/OA licenses (CC-BY, CC-BY-NC, CC0).
- **Rate Limit Policy**: Max 10 requests/sec with polite User-Agent.
- **Link Template**: `https://europepmc.org/article/MED/{identifier}`
- **Empirical Test Call**:
  - Request: `GET https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=ext_id:20448178%20src:med&resultType=core&format=json`
  - Status: `200 OK`
  - Observed Response Fields: `resultList.result[0].title` ("A draft sequence of the Neandertal genome."), `resultList.result[0].abstractText` (873 chars), `resultList.result[0].isOpenAccess` ("N"), `resultList.result[0].inEPMC` ("Y").

---

## 13. Ensembl Compara REST API
- **Official Documentation**: https://rest.ensembl.org/documentation/info/homology_symbol
- **Base URL**: `https://rest.ensembl.org`
- **Key Endpoints**:
  - Homology by Symbol: `GET /homology/symbol/{species}/{symbol}?type=orthologues`
  - Gene Lookup & Coordinates: `GET /lookup/symbol/{species}/{symbol}?expand=1`
  - Genomic Neighborhood: `GET /overlap/region/{species}/{region}:{start}-{end}?feature=gene`
- **ID Format (Regex)**: Ensembl Gene ID: `^ENS[A-Z]{0,4}G[0-9]{11}$`
- **License / Terms**: Open Access (EMBL-EBI / Wellcome Sanger Institute)
- **Rate Limit Policy**: Max 15 requests/sec with `Content-Type: application/json`.
- **Link Template**: `https://www.ensembl.org/{species}/Gene/Summary?g={identifier}`
- **Empirical Test Call**:
  - Request: `GET https://rest.ensembl.org/homology/symbol/homo_sapiens/HBA1?target_species=loxodonta_africana&type=orthologues`
  - Status: `200 OK`
  - Observed Response Fields: `data[0].homologies[0].type` ("ortholog_one2many"), `target.taxon_id` (9785), `target.protein_id` ("ENSLAFP00000013265"), `target.perc_id` (81.69).

---

## 14. OrthoDB REST API
- **Official Documentation**: https://www.orthodb.org/?page=api
- **Base URL**: `https://data.orthodb.org/current`
- **Key Endpoints**:
  - Ortholog Search: `GET /search?query={query}`
  - Group Details: `GET /group?id={group_id}`
- **ID Format (Regex)**: `^[0-9]+at[0-9]+$`
- **License / Terms**: Creative Commons Attribution (CC-BY 4.0)
- **Rate Limit Policy**: Standard academic etiquette.
- **Link Template**: `https://www.orthodb.org/?query={identifier}`
- **Empirical Test Call**:
  - Request: `GET https://data.orthodb.org/current/search?query=HBA1`
  - Status: `200 OK`
  - Observed Response Fields: `data[0]` ("6114439at2759").

