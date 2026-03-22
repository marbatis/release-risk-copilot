"""Application entrypoint for Release Risk Copilot MVP."""

from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="Release Risk Copilot",
    version="0.1.0",
    description="Deterministic release-risk decision support with mock memo provider.",
)
app.include_router(router)


@app.get("/")
def root() -> dict[str, str]:
    """API root response."""

    return {
        "name": "Release Risk Copilot",
        "phase": "mvp-foundation",
        "status": "ready",
    }
