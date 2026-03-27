"""Application entrypoint for Release Risk Copilot MVP."""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.routes import router
from app.api.web import router as web_router
from app.config import get_settings
from app.db import init_db

settings = get_settings()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


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


def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Try again later."})


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Deterministic release-risk decision support with explain-only memo provider.",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(web_router)
app.include_router(router)
