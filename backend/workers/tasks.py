"""
Ingestion task chain, per the implementation plan:

    parse_document -> chunk_document -> dedup_check -> embed_chunks ->
    upsert_to_qdrant -> update_manifest_status

Each stage is its own Celery task (not one monolithic function) so failures
are retryable at the granular level, chained with Celery's `chain()`
primitive.

NOT executed live in the build sandbox (no Redis broker running there). The
pure-Python logic each task delegates to (chunking.py, dedup.py) IS unit
tested directly (bypassing Celery) in backend/tests/. Verify the actual
Celery chain execution against a real broker on the target machine per
HANDOFF.md.
"""
from __future__ import annotations

import json
from pathlib import Path

from backend.config import get_settings
from backend.core.chunking import Block, ChunkType, chunk_document
from backend.core.embeddings import build_embedding_model
from backend.core.vector_store import VectorStore
from backend.utils.dedup import diff_chunks
from backend.utils.pdf_parser import parse_pdf
from backend.workers.celery_app import celery_app

MANIFEST_PATH = Path("data/processed/manifest.jsonl")


def _update_manifest_status(doc_id: str, status: str, error: str | None = None) -> None:
    """Rewrite the manifest row for doc_id with a new status. Simple
    read-modify-write since manifest.jsonl is expected to be small enough
    for a portfolio-scale corpus; swap for a real DB if this grows."""
    if not MANIFEST_PATH.exists():
        return
    rows = [json.loads(line) for line in MANIFEST_PATH.read_text().splitlines() if line.strip()]
    for row in rows:
        if row.get("doc_id") == doc_id:
            row["status"] = status
            if error:
                row["error"] = error
    MANIFEST_PATH.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


@celery_app.task(bind=True, max_retries=3)
def parse_document_task(self, doc_id: str, raw_path: str):
    try:
        blocks = parse_pdf(raw_path)
        return {"doc_id": doc_id, "blocks": [b.__dict__ for b in blocks]}
    except Exception as exc:  # noqa: BLE001 - deliberately broad; logged to manifest
        _update_manifest_status(doc_id, "failed", str(exc))
        raise self.retry(exc=exc, countdown=30)


@celery_app.task
def chunk_document_task(parsed: dict):
    settings = get_settings()
    blocks = [Block(text=b["text"], section=b["section"], block_type=ChunkType(b["block_type"]), page_number=b["page_number"]) for b in parsed["blocks"]]
    chunks = chunk_document(
        doc_id=parsed["doc_id"],
        blocks=blocks,
        target_tokens=settings.chunk_target_tokens,
        overlap_tokens=settings.chunk_overlap_tokens,
        hard_cap_tokens=settings.chunk_hard_cap_tokens,
    )
    return {"doc_id": parsed["doc_id"], "chunks": [c.__dict__ for c in chunks]}


@celery_app.task
def dedup_check_task(chunked: dict):
    settings = get_settings()
    store = VectorStore(
        collection_name=settings.qdrant_collection_name,
        url=None if settings.qdrant_use_local_mode else settings.qdrant_url,
        local_path=settings.qdrant_local_path if settings.qdrant_use_local_mode else None,
        vector_size=settings.embedding_dimension,
    )
    existing_hashes = store.get_existing_hashes(chunked["doc_id"])

    from backend.core.chunking import Chunk, ChunkType as CT

    chunk_objs = [
        Chunk(
            doc_id=c["doc_id"],
            chunk_index=c["chunk_index"],
            section=c["section"],
            chunk_type=CT(c["chunk_type"]),
            page_number=c["page_number"],
            text=c["text"],
            truncated=c["truncated"],
            content_hash=c["content_hash"],
        )
        for c in chunked["chunks"]
    ]
    result = diff_chunks(chunk_objs, existing_hashes)
    return {
        "doc_id": chunked["doc_id"],
        "chunks_to_upsert": [c.__dict__ for c in result.chunks_to_upsert],
        "stale_chunk_indices_to_delete": result.stale_chunk_indices_to_delete,
    }


@celery_app.task
def embed_chunks_task(dedup_result: dict):
    settings = get_settings()
    model = build_embedding_model(settings.embedding_model_name, settings.embedding_batch_size)
    texts = [c["text"] for c in dedup_result["chunks_to_upsert"]]
    vectors = model.embed(texts) if texts else []
    return {**dedup_result, "vectors": vectors}


@celery_app.task
def upsert_to_qdrant_task(embedded: dict):
    settings = get_settings()
    store = VectorStore(
        collection_name=settings.qdrant_collection_name,
        url=None if settings.qdrant_use_local_mode else settings.qdrant_url,
        local_path=settings.qdrant_local_path if settings.qdrant_use_local_mode else None,
        vector_size=settings.embedding_dimension,
    )
    store.delete_chunks(embedded["doc_id"], embedded["stale_chunk_indices_to_delete"])

    points = []
    for chunk, vector in zip(embedded["chunks_to_upsert"], embedded["vectors"]):
        points.append(
            {
                "id": f"{chunk['doc_id']}::{chunk['chunk_index']}",
                "dense_vector": vector,
                "payload": {
                    "doc_id": chunk["doc_id"],
                    "chunk_index": chunk["chunk_index"],
                    "section": chunk["section"],
                    "chunk_type": chunk["chunk_type"],
                    "chunk_text": chunk["text"],
                    "content_hash": chunk["content_hash"],
                },
            }
        )
    if points:
        store.upsert_chunks(points)
    return {"doc_id": embedded["doc_id"], "upserted": len(points)}


@celery_app.task
def update_manifest_status_task(upsert_result: dict):
    _update_manifest_status(upsert_result["doc_id"], "ingested")
    return upsert_result


def build_ingestion_chain(doc_id: str, raw_path: str):
    """Assemble the full Celery chain for a single document, per spec."""
    from celery import chain

    return chain(
        parse_document_task.s(doc_id, raw_path),
        chunk_document_task.s(),
        dedup_check_task.s(),
        embed_chunks_task.s(),
        upsert_to_qdrant_task.s(),
        update_manifest_status_task.s(),
    )
