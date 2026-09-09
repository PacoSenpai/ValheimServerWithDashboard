"""Punto de entrada del backend FastAPI."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import router as api_router
from app.api.ws import router as ws_router
from app.core.config import get_settings
from app.core.events import bus
from app.core.lifespan import Lifespan
from app.core.logging import configure_logging

configure_logging()
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ls = Lifespan(get_settings(), bus)
    await ls.startup()
    app.state.registry = ls.registry
    try:
        yield
    finally:
        await ls.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Valheim Dashboard",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.panel.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    app.include_router(ws_router)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    frontend_dist = Path(os.environ.get("FRONTEND_DIST", "/opt/valheim-dashboard/frontend/dist"))
    if frontend_dist.is_dir():
        assets = frontend_dist / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/", include_in_schema=False)
        async def root_index() -> FileResponse:
            return FileResponse(frontend_dist / "index.html")

        @app.get("/{path:path}", include_in_schema=False)
        async def spa_fallback(path: str) -> FileResponse:
            full = frontend_dist / path
            if full.is_file():
                return FileResponse(full)
            return FileResponse(frontend_dist / "index.html")
    else:
        @app.get("/", include_in_schema=False)
        async def root_index_dev() -> dict[str, str]:
            return {
                "status": "ok",
                "frontend": "no compilado",
                "hint": "make build o usa el dev server (vite).",
            }

    return app


app = create_app()
