"""
Deduplication logic for re-ingestion.

When a document is re-ingested (same DOI, newer retrieved_at), we diff the
new chunk hashes against whatever is already stored for that doc_id, and
report exactly which chunks are new/changed/stale-to-delete. This module is
pure logic — it takes hash sets in and returns a diff, so it has no DB
dependency and is trivially testable. The caller (tasks.py) is responsible
for fetching existing hashes from Qdrant and applying the resulting diff.
"""
from __future__ import annotations

from dataclasses import dataclass

from backend.core.chunking import Chunk


@dataclass
class DedupResult:
    chunks_to_upsert: list[Chunk]
    stale_chunk_indices_to_delete: list[int]
    unchanged_count: int


def diff_chunks(
    new_chunks: list[Chunk],
    existing_hash_by_index: dict[int, str],
) -> DedupResult:
    """
    Args:
        new_chunks: freshly computed chunks for this ingestion pass.
        existing_hash_by_index: {chunk_index: content_hash} currently stored
            in the vector DB for this doc_id.

    Returns:
        DedupResult telling the caller which chunks need (re-)embedding and
        upserting, and which stale chunk_indices (present before but not in
        the new set, or changed) should be deleted from the vector store.
    """
    new_by_index = {c.chunk_index: c for c in new_chunks}

    to_upsert: list[Chunk] = []
    unchanged = 0
    for idx, chunk in new_by_index.items():
        old_hash = existing_hash_by_index.get(idx)
        if old_hash is None or old_hash != chunk.content_hash:
            to_upsert.append(chunk)
        else:
            unchanged += 1

    # Indices that existed before but are gone or changed in the new version.
    stale_indices = [
        idx
        for idx in existing_hash_by_index
        if idx not in new_by_index or existing_hash_by_index[idx] != new_by_index[idx].content_hash
    ]

    return DedupResult(
        chunks_to_upsert=to_upsert,
        stale_chunk_indices_to_delete=stale_indices,
        unchanged_count=unchanged,
    )
