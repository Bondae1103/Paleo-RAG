"""
Taxonomy resolution via GBIF (extant species) and PBDB (paleontological
taxa), per the implementation plan's instruction to NOT hand-roll a
common-name lookup table.

Design:
- GBIF's species/match endpoint is the primary resolver for common name ->
  scientific binomial.
- PBDB is cross-checked because GBIF is extant-species-biased and will
  sometimes fail on extinct paleo taxa (or resolve to the wrong rank).
- Results are cached (Redis in production; an in-memory dict fallback here
  so this module works standalone in tests/dev without a Redis server).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional, Protocol

import httpx


class CacheLike(Protocol):
    def get(self, key: str) -> Optional[str]: ...
    def setex(self, key: str, ttl_seconds: int, value: str) -> None: ...


class InMemoryCache:
    """Drop-in replacement for a redis.Redis client's get/setex, for tests
    and for environments without Redis available."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def get(self, key: str) -> Optional[str]:
        return self._store.get(key)

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        # TTL is ignored in the in-memory fallback; acceptable for dev/test.
        self._store[key] = value


@dataclass
class TaxonResolution:
    input_name: str
    scientific_name: Optional[str] = None
    common_names: list[str] = field(default_factory=list)
    rank: Optional[str] = None
    source: Optional[str] = None  # "gbif" | "pbdb" | "unresolved"
    geological_period: Optional[str] = None


def _normalize(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


class TaxonomyClient:
    def __init__(
        self,
        gbif_api_base: str,
        pbdb_api_base: str,
        cache: Optional[CacheLike] = None,
        cache_ttl_seconds: int = 60 * 60 * 24 * 30,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self.gbif_api_base = gbif_api_base.rstrip("/")
        self.pbdb_api_base = pbdb_api_base.rstrip("/")
        self.cache = cache or InMemoryCache()
        self.cache_ttl_seconds = cache_ttl_seconds
        self.http = http_client or httpx.Client(timeout=10.0)

    def _cache_key(self, name: str) -> str:
        return f"taxon:{_normalize(name)}"

    def resolve(self, name: str) -> TaxonResolution:
        cache_key = self._cache_key(name)
        cached = self.cache.get(cache_key)
        if cached:
            data = json.loads(cached)
            return TaxonResolution(**data)

        result = self._resolve_uncached(name)
        self.cache.setex(cache_key, self.cache_ttl_seconds, json.dumps(result.__dict__))
        return result

    def _resolve_uncached(self, name: str) -> TaxonResolution:
        gbif_result = self._query_gbif(name)
        if gbif_result and gbif_result.scientific_name:
            # Still attempt a PBDB cross-check to pick up geological period
            # metadata, but GBIF's name resolution wins for extant taxa.
            pbdb_result = self._query_pbdb(gbif_result.scientific_name)
            if pbdb_result:
                gbif_result.geological_period = pbdb_result.geological_period
            return gbif_result

        pbdb_result = self._query_pbdb(name)
        if pbdb_result and pbdb_result.scientific_name:
            return pbdb_result

        return TaxonResolution(input_name=name, source="unresolved")

    def _query_gbif(self, name: str) -> Optional[TaxonResolution]:
        try:
            resp = self.http.get(f"{self.gbif_api_base}/species/match", params={"name": name})
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError):
            return None

        scientific_name = data.get("scientificName") or data.get("canonicalName")
        if not scientific_name or data.get("matchType") == "NONE":
            return None

        return TaxonResolution(
            input_name=name,
            scientific_name=scientific_name,
            common_names=[name] if name.lower() != scientific_name.lower() else [],
            rank=data.get("rank"),
            source="gbif",
        )

    def _query_pbdb(self, name: str) -> Optional[TaxonResolution]:
        try:
            resp = self.http.get(f"{self.pbdb_api_base}/taxa/list.json", params={"name": name, "show": "phylo"})
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError):
            return None

        records = data.get("records") or []
        if not records:
            return None

        record = records[0]
        scientific_name = record.get("nam") or record.get("taxon_name")
        if not scientific_name:
            return None

        return TaxonResolution(
            input_name=name,
            scientific_name=scientific_name,
            rank=record.get("rnk_name") or record.get("rank"),
            source="pbdb",
            geological_period=record.get("early_interval") or record.get("oei"),
        )

    def expand_query_terms(self, query: str, known_taxa: Optional[list[str]] = None) -> list[str]:
        """
        Given a raw user query, return a list of additional search terms
        (scientific names) to widen the BM25/sparse side of hybrid search.
        The dense embedding of the *original* query text is left unmodified
        elsewhere in the pipeline, per spec.
        """
        candidates = known_taxa or []
        expansions: list[str] = []
        text_lower = query.lower()
        for candidate in candidates:
            if candidate.lower() in text_lower:
                resolution = self.resolve(candidate)
                if resolution.scientific_name:
                    expansions.append(resolution.scientific_name)

        if not expansions:
            # Fall back to attempting resolution of the whole query as a
            # last resort (cheap since it's cached), useful when the known
            # taxa list is empty/stale.
            resolution = self.resolve(query)
            if resolution.scientific_name:
                expansions.append(resolution.scientific_name)

        return expansions
