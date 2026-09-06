"""
Qdrant vector store wrapper: hybrid (dense + BM25 sparse) search combined via
Reciprocal Rank Fusion, plus first-class payload filtering (taxon, period,
year range).

This module supports Qdrant's embedded/local mode (`location=":memory:"` or
a file path) as well as a real server URL, so it is fully testable without
Docker (see backend/tests/test_vector_store.py).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels


RRF_K = 60  # standard RRF smoothing constant

_POINT_ID_NAMESPACE = uuid.UUID("12345678-1234-5678-1234-567812345678")


def _to_qdrant_point_id(raw_id: str | int) -> str:
    """Qdrant's local/embedded mode requires point IDs to be either an
    unsigned int or a valid UUID string. Our natural point IDs are
    human-readable strings like 'doc123::4', so we deterministically map
    them to a UUID5 (stable across re-upserts of the same doc_id/chunk_index
    pair, which is required for delete/update-by-id and for the dedup
    upsert-in-place behavior). The original human-readable id is preserved
    in the payload's doc_id/chunk_index fields, not lost."""
    if isinstance(raw_id, int):
        return str(raw_id)
    return str(uuid.uuid5(_POINT_ID_NAMESPACE, raw_id))


@dataclass
class SearchFilters:
    taxon_scientific_name: Optional[str] = None
    geological_period: Optional[str] = None
    publication_year_min: Optional[int] = None
    publication_year_max: Optional[int] = None


@dataclass
class SearchResult:
    doc_id: str
    chunk_index: int
    section: str
    chunk_type: str
    text: str
    score: float


class VectorStore:
    def __init__(
        self,
        collection_name: str = "paleo_chunks",
        url: Optional[str] = None,
        local_path: Optional[str] = None,
        vector_size: int = 768,
        client: Optional[QdrantClient] = None,
    ) -> None:
        if client is not None:
            self.client = client
        elif local_path:
            self.client = QdrantClient(path=local_path)
        elif url:
            self.client = QdrantClient(url=url)
        else:
            self.client = QdrantClient(location=":memory:")

        self.collection_name = collection_name
        self.vector_size = vector_size

    def ensure_collection(self) -> None:
        existing = [c.name for c in self.client.get_collections().collections]
        if self.collection_name in existing:
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config={"dense": qmodels.VectorParams(size=self.vector_size, distance=qmodels.Distance.COSINE)},
        )

    def upsert_chunks(
        self,
        points: list[dict],
    ) -> None:
        """
        points: list of dicts each with keys:
            id (int|str), dense_vector (list[float]), payload (dict) with at
            least doc_id, chunk_index, section, chunk_type, chunk_text, and
            optionally taxon_scientific_name, geological_period,
            publication_year.
        """
        self.ensure_collection()
        qpoints = [
            qmodels.PointStruct(
                id=_to_qdrant_point_id(p["id"]),
                vector={"dense": p["dense_vector"]},
                payload=p["payload"],
            )
            for p in points
        ]
        self.client.upsert(collection_name=self.collection_name, points=qpoints)

    def delete_chunks(self, doc_id: str, chunk_indices: list[int]) -> None:
        if not chunk_indices:
            return
        self.ensure_collection()
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(key="doc_id", match=qmodels.MatchValue(value=doc_id)),
                        qmodels.FieldCondition(key="chunk_index", match=qmodels.MatchAny(any=chunk_indices)),
                    ]
                )
            ),
        )

    def get_existing_hashes(self, doc_id: str) -> dict[int, str]:
        """Fetch {chunk_index: content_hash} currently stored for a doc_id,
        used by the dedup diff step during re-ingestion."""
        self.ensure_collection()
        result = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=qmodels.Filter(
                must=[qmodels.FieldCondition(key="doc_id", match=qmodels.MatchValue(value=doc_id))]
            ),
            limit=10_000,
            with_payload=True,
        )
        points, _ = result
        return {p.payload["chunk_index"]: p.payload["content_hash"] for p in points if "content_hash" in p.payload}

    def _build_filter(self, filters: Optional[SearchFilters]) -> Optional[qmodels.Filter]:
        if filters is None:
            return None
        conditions = []
        if filters.taxon_scientific_name:
            conditions.append(
                qmodels.FieldCondition(
                    key="taxon_scientific_name", match=qmodels.MatchValue(value=filters.taxon_scientific_name)
                )
            )
        if filters.geological_period:
            conditions.append(
                qmodels.FieldCondition(
                    key="geological_period", match=qmodels.MatchValue(value=filters.geological_period)
                )
            )
        if filters.publication_year_min is not None or filters.publication_year_max is not None:
            conditions.append(
                qmodels.FieldCondition(
                    key="publication_year",
                    range=qmodels.Range(
                        gte=filters.publication_year_min,
                        lte=filters.publication_year_max,
                    ),
                )
            )
        if not conditions:
            return None
        return qmodels.Filter(must=conditions)

    def dense_search(
        self, query_vector: list[float], top_k: int, filters: Optional[SearchFilters] = None
    ) -> list[SearchResult]:
        self.ensure_collection()
        q_filter = self._build_filter(filters)
        hits = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            using="dense",
            limit=top_k,
            query_filter=q_filter,
        ).points
        return [
            SearchResult(
                doc_id=h.payload["doc_id"],
                chunk_index=h.payload["chunk_index"],
                section=h.payload.get("section", ""),
                chunk_type=h.payload.get("chunk_type", "text"),
                text=h.payload.get("chunk_text", ""),
                score=h.score,
            )
            for h in hits
        ]

    def scroll_all_chunks(self) -> list[tuple[tuple[str, int], str]]:
        """Scroll through all points in the collection and return [((doc_id, chunk_index), chunk_text)]."""
        self.ensure_collection()
        corpus: list[tuple[tuple[str, int], str]] = []
        offset = None
        while True:
            points, next_offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=1000,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for p in points:
                payload = p.payload or {}
                doc_id = payload.get("doc_id")
                chunk_index = payload.get("chunk_index")
                text = payload.get("chunk_text", "")
                if doc_id is not None and chunk_index is not None and text:
                    corpus.append(((doc_id, chunk_index), text))
            if next_offset is None:
                break
            offset = next_offset
        return corpus

    def hybrid_search(
        self,
        query_vector: list[float],
        sparse_ranked_doc_keys: list[tuple[str, int]],
        top_k: int,
        filters: Optional[SearchFilters] = None,
    ) -> list[SearchResult]:
        """
        Combine dense search results with an externally-computed sparse
        (BM25) ranking via Reciprocal Rank Fusion.

        sparse_ranked_doc_keys: ordered list of (doc_id, chunk_index) tuples,
        best match first, as produced by the BM25 index (see
        rag_pipeline.py). Kept as an explicit parameter (rather than baked
        into this class) so the sparse backend can be swapped per
        DECISIONS.md without changing this method's contract.
        """
        dense_results = self.dense_search(query_vector, top_k=max(top_k * 3, 20), filters=filters)
        dense_key = lambda r: (r.doc_id, r.chunk_index)

        rrf_scores: dict[tuple[str, int], float] = {}
        result_lookup: dict[tuple[str, int], SearchResult] = {}

        for rank, result in enumerate(dense_results):
            key = dense_key(result)
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (RRF_K + rank + 1)
            result_lookup[key] = result

        for rank, key in enumerate(sparse_ranked_doc_keys):
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (RRF_K + rank + 1)

        fused = sorted(rrf_scores.items(), key=lambda kv: kv[1], reverse=True)

        # Retrieve missing payloads for sparse-only candidates that could make top_k
        missing_keys = [key for key, _ in fused[: top_k * 3] if key not in result_lookup]
        if missing_keys:
            point_ids = [_to_qdrant_point_id(f"{doc_id}::{chunk_idx}") for doc_id, chunk_idx in missing_keys]
            retrieved_points = self.client.retrieve(
                collection_name=self.collection_name,
                ids=point_ids,
                with_payload=True,
            )
            for p in retrieved_points:
                payload = p.payload or {}
                if filters:
                    if filters.taxon_scientific_name and payload.get("taxon_scientific_name") != filters.taxon_scientific_name:
                        continue
                    if filters.geological_period and payload.get("geological_period") != filters.geological_period:
                        continue
                    if filters.publication_year_min is not None and payload.get("publication_year", -99999) < filters.publication_year_min:
                        continue
                    if filters.publication_year_max is not None and payload.get("publication_year", 99999) > filters.publication_year_max:
                        continue
                doc_id = payload.get("doc_id")
                chunk_index = payload.get("chunk_index")
                if doc_id is not None and chunk_index is not None:
                    k = (doc_id, chunk_index)
                    result_lookup[k] = SearchResult(
                        doc_id=doc_id,
                        chunk_index=chunk_index,
                        section=payload.get("section", ""),
                        chunk_type=payload.get("chunk_type", "text"),
                        text=payload.get("chunk_text", ""),
                        score=0.0,
                    )

        final: list[SearchResult] = []
        for key, score in fused:
            if key in result_lookup:
                r = result_lookup[key]
                final.append(SearchResult(r.doc_id, r.chunk_index, r.section, r.chunk_type, r.text, score))
                if len(final) == top_k:
                    break
        return final
