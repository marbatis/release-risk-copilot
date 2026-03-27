"""Application entrypoint for Release Risk Copilot MVP."""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.api.web import router as web_router
from app.config import get_settings
from app.db import init_db

settings = get_settings()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize required local resources at startup."""

    init_db()
    if settings.openai_api_key:
        logger.info("Explanation provider mode: openai (%s)", settings.openai_model)
    else:
        logger.info("Explanation provider mode: mock (OPENAI_API_KEY not set)")
    if settings.upload_max_bytes <= 0:
        logger.warning("UPLOAD_MAX_BYTES is non-positive; defaulting behavior may reject uploads.")
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Deterministic release-risk decision support with explain-only memo provider.",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(web_router)
app.include_router(router)
