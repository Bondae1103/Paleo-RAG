from __future__ import annotations

from fastapi import FastAPI

from backend.api.routes import router
from backend.config import get_settings
from backend.utils.logging_config import configure_logging

settings = get_settings()
configure_logging(level=settings.log_level, json_output=settings.log_json)

app = FastAPI(title="PaleoRAG", description="Phylogenetic Context Engine", version="0.1.0")
app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host=settings.api_host, port=settings.api_port, reload=True)
