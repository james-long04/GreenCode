"""GreenCode API — FastAPI application entry point.

Run locally with:  uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.routes import router
from app.config import get_settings
from app.db.session import init_db
from app.logbuffer import install as install_log_buffer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("greencode")
install_log_buffer()


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    settings = get_settings()
    try:
        init_db()
        log.info("database ready (%s)", settings.database_url.split("@")[-1])
    except Exception as err:  # noqa: BLE001
        log.error("database initialisation failed: %s", err)
    yield


app = FastAPI(
    title="GreenCode API",
    version="0.1.0",
    description="Static-analysis-guided AI optimisation for sustainable Python and SQL — evidence pipeline API.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")
app.include_router(admin_router, prefix="/api/admin")


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "GreenCode", "docs": "/docs", "api": "/api/health"}
