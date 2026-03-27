"""Runtime configuration for Release Risk Copilot."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from os import getenv
from typing import Optional


@dataclass(frozen=True)
class Settings:
    """Typed application settings loaded from environment variables."""

    app_name: str = "Release Risk Copilot"
    app_version: str = "0.2.0"
    database_url: str = "sqlite:///./release_risk.db"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-5-mini"
    upload_max_bytes: int = 200_000


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached environment-backed settings."""

    return Settings(
        database_url=getenv("DATABASE_URL", "sqlite:///./release_risk.db"),
        openai_api_key=getenv("OPENAI_API_KEY"),
        openai_model=getenv("OPENAI_MODEL", "gpt-5-mini"),
        upload_max_bytes=int(getenv("UPLOAD_MAX_BYTES", "200000")),
    )
