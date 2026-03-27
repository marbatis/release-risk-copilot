"""Global pytest configuration for deterministic local test runtime."""

from __future__ import annotations

import os
from pathlib import Path

TEST_DB_PATH = Path(__file__).resolve().parent / "test_release_risk.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ.pop("OPENAI_API_KEY", None)

if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()
