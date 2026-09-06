"""Pydantic models for request/response validation across the API."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class IngestSource(str, Enum):
    pmc_oa = "pmc_oa"
    biorxiv = "biorxiv"
    manual_upload = "manual_upload"


class UploadRequest(BaseModel):
    """Used for the DOI/URL ingestion path (multipart file upload is handled
    separately by FastAPI's UploadFile in the route signature)."""

    doi_or_url: Optional[str] = None
    source: IngestSource = IngestSource.manual_upload


class UploadResponse(BaseModel):
    task_id: str
    status: str = "queued"


class TaskStatusResponse(BaseModel):
    task_id: str
    state: str  # PENDING | STARTED | SUCCESS | FAILURE
    error: Optional[str] = None
    result: Optional[dict] = None


class ChatFilters(BaseModel):
    taxon_scientific_name: Optional[str] = None
    geological_period: Optional[str] = None
    publication_year_min: Optional[int] = None
    publication_year_max: Optional[int] = None


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1)
    filters: Optional[ChatFilters] = None
    top_k: Optional[int] = None


class RetrievedChunk(BaseModel):
    doc_id: str
    chunk_index: int
    section: Optional[str] = None
    chunk_type: str = "text"
    score: float
    text: str


class CitationWarning(BaseModel):
    cited_marker: str
    reason: str


class ChatStreamFinalEvent(BaseModel):
    retrieved_chunks: list[RetrievedChunk]
    citation_warnings: list[CitationWarning] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    qdrant_ok: bool
    redis_ok: bool
    llm_ok: bool
    detail: Optional[dict] = None
