"""
Celery application setup. Requires a running Redis broker to actually
execute tasks — NOT started/tested live in the build sandbox (no Redis
server was running there; only the `redis` and `celery` Python packages
were installed and import-tested). Verify with a real broker on the target
machine per HANDOFF.md.
"""
from __future__ import annotations

from celery import Celery

from backend.config import get_settings

settings = get_settings()

celery_app = Celery(
    "paleo_rag",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.autodiscover_tasks(["backend.workers"])
