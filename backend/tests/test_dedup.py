from backend.core.chunking import Chunk, ChunkType
from backend.utils.dedup import diff_chunks


def _chunk(idx: int, text: str) -> Chunk:
    return Chunk(doc_id="docX", chunk_index=idx, section="Results", chunk_type=ChunkType.TEXT, page_number=1, text=text)


def test_unchanged_chunks_are_not_reupserted():
    new_chunks = [_chunk(0, "same text"), _chunk(1, "also same")]
    existing = {0: new_chunks[0].content_hash, 1: new_chunks[1].content_hash}

    result = diff_chunks(new_chunks, existing)

    assert result.chunks_to_upsert == []
    assert result.unchanged_count == 2
    assert result.stale_chunk_indices_to_delete == []


def test_changed_chunk_is_reupserted_and_flagged_stale():
    new_chunks = [_chunk(0, "updated text")]
    existing = {0: "old-hash-that-does-not-match"}

    result = diff_chunks(new_chunks, existing)

    assert len(result.chunks_to_upsert) == 1
    assert result.chunks_to_upsert[0].chunk_index == 0
    assert 0 in result.stale_chunk_indices_to_delete


def test_new_chunk_with_no_prior_history_is_upserted_not_stale():
    new_chunks = [_chunk(0, "brand new content")]
    existing: dict[int, str] = {}

    result = diff_chunks(new_chunks, existing)

    assert len(result.chunks_to_upsert) == 1
    assert result.stale_chunk_indices_to_delete == []


def test_removed_chunk_is_flagged_for_deletion():
    new_chunks = [_chunk(0, "still here")]
    existing = {0: new_chunks[0].content_hash, 1: "hash-of-a-chunk-that-no-longer-exists"}

    result = diff_chunks(new_chunks, existing)

    assert result.chunks_to_upsert == []
    assert result.stale_chunk_indices_to_delete == [1]
