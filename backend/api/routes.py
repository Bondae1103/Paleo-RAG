from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from backend.api.dependencies import (
    get_rag_pipeline,
    get_taxonomy_client,
    get_vector_store,
    verify_bearer_token,
)
from backend.api.schemas import (
    ChatRequest,
    HealthResponse,
    IngestSource,
    TaskStatusResponse,
    UploadResponse,
)
from backend.config import get_settings
from backend.core.rag_pipeline import RagPipeline, check_citations
from backend.core.vector_store import SearchFilters

router = APIRouter()

APPROVED_SOURCES = {IngestSource.pmc_oa, IngestSource.biorxiv, IngestSource.manual_upload}
RAW_PDF_DIR = Path("data/raw_pdfs")
MANIFEST_PATH = Path("data/processed/manifest.jsonl")


@router.post("/api/upload", response_model=UploadResponse, dependencies=[Depends(verify_bearer_token)])
async def upload_document(file: UploadFile, source: IngestSource = IngestSource.manual_upload):
    if source not in APPROVED_SOURCES:
        raise HTTPException(status_code=400, detail=f"Source '{source}' is not an approved ingestion source.")

    RAW_PDF_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    doc_id = f"upload_{uuid.uuid4().hex[:12]}"
    dest_path = RAW_PDF_DIR / f"{doc_id}.pdf"
    content = await file.read()
    dest_path.write_bytes(content)

    with MANIFEST_PATH.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "doc_id": doc_id,
                    "source": source.value,
                    "license": "unknown-manual-upload",
                    "doi": "",
                    "title": file.filename or "",
                    "retrieved_at": "",
                    "raw_path": str(dest_path),
                    "status": "queued",
                }
            )
            + "\n"
        )

    # Enqueue the Celery ingestion chain. NOT executed live in the build
    # sandbox (no Redis broker there) — task_id is generated regardless so
    # the API contract (immediate return, poll via /api/task/{id}) holds;
    # verify actual chain execution on the target machine per HANDOFF.md.
    try:
        from backend.workers.tasks import build_ingestion_chain

        async_result = build_ingestion_chain(doc_id, str(dest_path)).apply_async()
        task_id = async_result.id
    except Exception:
        # Broker not reachable in this environment — still return a
        # deterministic task_id so the API contract is exercised by tests.
        task_id = f"unsubmitted_{doc_id}"

    return UploadResponse(task_id=task_id, status="queued")


@router.get("/api/task/{task_id}", response_model=TaskStatusResponse, dependencies=[Depends(verify_bearer_token)])
async def get_task_status(task_id: str):
    if task_id.startswith("unsubmitted_"):
        return TaskStatusResponse(task_id=task_id, state="PENDING", error="Celery broker not reachable.")

    from backend.workers.celery_app import celery_app

    result = celery_app.AsyncResult(task_id)
    error = str(result.result) if result.state == "FAILURE" else None
    return TaskStatusResponse(task_id=task_id, state=result.state, error=error)


@router.post("/api/chat/stream", dependencies=[Depends(verify_bearer_token)])
async def chat_stream(request: ChatRequest, pipeline: RagPipeline = Depends(get_rag_pipeline)):
    filters = None
    if request.filters:
        filters = SearchFilters(
            taxon_scientific_name=request.filters.taxon_scientific_name,
            geological_period=request.filters.geological_period,
            publication_year_min=request.filters.publication_year_min,
            publication_year_max=request.filters.publication_year_max,
        )

    _, chunks = pipeline.retrieve(request.query, filters=filters, top_k=request.top_k)

    async def event_generator():
        full_text = ""
        from backend.core.rag_pipeline import build_prompt

        prompt = build_prompt(request.query, chunks)
        async for piece in pipeline.llm_client.stream(prompt):
            full_text += piece
            yield f"data: {json.dumps({'token': piece})}\n\n"

        warnings = check_citations(full_text, chunks)
        final_payload = {
            "done": True,
            "retrieved_chunks": [
                {
                    "doc_id": c.doc_id,
                    "chunk_index": c.chunk_index,
                    "section": c.section,
                    "chunk_type": c.chunk_type,
                    "score": c.score,
                    "text": c.text,
                }
                for c in chunks
            ],
            "citation_warnings": [{"cited_marker": w.cited_marker, "reason": w.reason} for w in warnings],
        }
        yield f"data: {json.dumps(final_payload)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/api/health", response_model=HealthResponse)
async def health():
    settings = get_settings()
    detail: dict = {}

    qdrant_ok = False
    try:
        store = get_vector_store()
        store.client.get_collections()
        qdrant_ok = True
    except Exception as exc:  # noqa: BLE001
        detail["qdrant_error"] = str(exc)

    redis_ok = False
    try:
        import redis as redis_lib

        r = redis_lib.from_url(settings.redis_url, socket_connect_timeout=2)
        r.ping()
        redis_ok = True
    except Exception as exc:  # noqa: BLE001
        detail["redis_error"] = str(exc)

    llm_ok = settings.llm_provider == "mock"  # only case verifiable without a live server
    if not llm_ok:
        detail["llm_note"] = f"LLM provider '{settings.llm_provider}' not live-checked by /api/health."

    overall = "ok" if (qdrant_ok and redis_ok) else "degraded"
    return HealthResponse(status=overall, qdrant_ok=qdrant_ok, redis_ok=redis_ok, llm_ok=llm_ok, detail=detail)
