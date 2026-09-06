"""
Script to run the full ingestion chain across all downloaded documents in the manifest,
populating the local Qdrant collection at data/qdrant_storage.
"""
from __future__ import annotations

import json
from pathlib import Path

from backend.config import get_settings
from backend.workers.tasks import (
    chunk_document_task,
    dedup_check_task,
    embed_chunks_task,
    parse_document_task,
    update_manifest_status_task,
    upsert_to_qdrant_task,
)

MANIFEST_PATH = Path("data/processed/manifest.jsonl")


def run_ingestion() -> None:
    if not MANIFEST_PATH.exists():
        print(f"Manifest not found at {MANIFEST_PATH}")
        return

    lines = [line.strip() for line in MANIFEST_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = [json.loads(line) for line in lines]
    print(f"Found {len(rows)} documents in manifest.")

    for i, row in enumerate(rows):
        doc_id = row["doc_id"]
        raw_path = row["raw_path"]
        if not Path(raw_path).exists():
            print(f"[{i+1}/{len(rows)}] Skipping {doc_id}: {raw_path} does not exist.")
            continue

        print(f"[{i+1}/{len(rows)}] Ingesting {doc_id} ({row.get('title', '')[:50]}...)...")
        try:
            # 1. Parse
            # Call parse_document_task.run or direct since we are running without Celery worker daemon
            parsed = parse_document_task(doc_id=doc_id, raw_path=raw_path)
            # 2. Chunk
            chunked = chunk_document_task(parsed)
            print(f"   -> Generated {len(chunked['chunks'])} chunks")
            # 3. Dedup
            deduped = dedup_check_task(chunked)
            print(f"   -> {len(deduped['chunks_to_upsert'])} chunks to upsert")
            # 4. Embed
            embedded = embed_chunks_task(deduped)
            # 5. Upsert
            upsert_res = upsert_to_qdrant_task(embedded)
            # 6. Update manifest
            update_manifest_status_task(upsert_res)
            print(f"   -> Successfully ingested {doc_id} ({upsert_res['upserted']} chunks).")
        except Exception as exc:
            print(f"   -> Error ingesting {doc_id}: {exc}")

    print("Corpus ingestion complete.")


if __name__ == "__main__":
    run_ingestion()
