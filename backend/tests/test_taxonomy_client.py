import httpx
import respx

from backend.utils.taxonomy_client import InMemoryCache, TaxonomyClient

GBIF_BASE = "https://api.gbif.org/v1"
PBDB_BASE = "https://paleobiodb.org/data1.2"


@respx.mock
def test_common_name_resolves_to_scientific_name_via_gbif():
    respx.get(f"{GBIF_BASE}/species/match").mock(
        return_value=httpx.Response(
            200, json={"scientificName": "Smilodon fatalis", "canonicalName": "Smilodon fatalis", "rank": "SPECIES", "matchType": "EXACT"}
        )
    )
    respx.get(f"{PBDB_BASE}/taxa/list.json").mock(
        return_value=httpx.Response(200, json={"records": [{"nam": "Smilodon fatalis", "early_interval": "Pleistocene"}]})
    )

    client = TaxonomyClient(gbif_api_base=GBIF_BASE, pbdb_api_base=PBDB_BASE, cache=InMemoryCache())
    result = client.resolve("saber-toothed cat")

    assert result.scientific_name == "Smilodon fatalis"
    assert result.source == "gbif"
    assert result.geological_period == "Pleistocene"


@respx.mock
def test_gbif_miss_falls_back_to_pbdb():
    respx.get(f"{GBIF_BASE}/species/match").mock(return_value=httpx.Response(200, json={"matchType": "NONE"}))
    respx.get(f"{PBDB_BASE}/taxa/list.json").mock(
        return_value=httpx.Response(200, json={"records": [{"nam": "Tyrannosaurus rex", "early_interval": "Maastrichtian"}]})
    )

    client = TaxonomyClient(gbif_api_base=GBIF_BASE, pbdb_api_base=PBDB_BASE, cache=InMemoryCache())
    result = client.resolve("T. rex")

    assert result.scientific_name == "Tyrannosaurus rex"
    assert result.source == "pbdb"


@respx.mock
def test_unresolvable_name_returns_unresolved_without_crashing():
    respx.get(f"{GBIF_BASE}/species/match").mock(return_value=httpx.Response(200, json={"matchType": "NONE"}))
    respx.get(f"{PBDB_BASE}/taxa/list.json").mock(return_value=httpx.Response(200, json={"records": []}))

    client = TaxonomyClient(gbif_api_base=GBIF_BASE, pbdb_api_base=PBDB_BASE, cache=InMemoryCache())
    result = client.resolve("not a real animal name")

    assert result.source == "unresolved"
    assert result.scientific_name is None


@respx.mock
def test_result_is_cached_and_second_call_makes_no_http_request():
    route = respx.get(f"{GBIF_BASE}/species/match").mock(
        return_value=httpx.Response(200, json={"scientificName": "Smilodon fatalis", "matchType": "EXACT"})
    )
    respx.get(f"{PBDB_BASE}/taxa/list.json").mock(return_value=httpx.Response(200, json={"records": []}))

    client = TaxonomyClient(gbif_api_base=GBIF_BASE, pbdb_api_base=PBDB_BASE, cache=InMemoryCache())
    client.resolve("saber-toothed cat")
    calls_after_first = route.call_count
    client.resolve("saber-toothed cat")

    assert route.call_count == calls_after_first  # no new call on cache hit


@respx.mock
def test_expand_query_terms_includes_resolved_scientific_name():
    respx.get(f"{GBIF_BASE}/species/match").mock(
        return_value=httpx.Response(200, json={"scientificName": "Smilodon fatalis", "matchType": "EXACT"})
    )
    respx.get(f"{PBDB_BASE}/taxa/list.json").mock(return_value=httpx.Response(200, json={"records": []}))

    client = TaxonomyClient(gbif_api_base=GBIF_BASE, pbdb_api_base=PBDB_BASE, cache=InMemoryCache())
    expansions = client.expand_query_terms(
        "what gene flow evidence exists for the saber-toothed cat?", known_taxa=["saber-toothed cat"]
    )

    assert "Smilodon fatalis" in expansions
