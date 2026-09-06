"""
Query expansion: wraps TaxonomyClient to widen the sparse/BM25 side of
hybrid search with resolved scientific names, while leaving the dense
embedding input untouched (per spec — embeddings already capture semantic
similarity, so mangling the query text there would only hurt).
"""
from __future__ import annotations

from dataclasses import dataclass

from backend.utils.taxonomy_client import TaxonomyClient


@dataclass
class ExpandedQuery:
    original_query: str
    dense_query_text: str  # unmodified original query
    sparse_query_terms: list[str]  # original query tokens + resolved taxa


def expand_query(
    query: str,
    taxonomy_client: TaxonomyClient,
    known_taxa: list[str] | None = None,
) -> ExpandedQuery:
    expansions = taxonomy_client.expand_query_terms(query, known_taxa=known_taxa)
    sparse_terms = query.split() + expansions
    return ExpandedQuery(
        original_query=query,
        dense_query_text=query,
        sparse_query_terms=sparse_terms,
    )
