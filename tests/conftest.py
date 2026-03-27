"""Global pytest configuration for deterministic local test runtime."""

from __future__ import annotations

import os

# Use in-memory SQLite for fully ephemeral test isolation.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.pop("OPENAI_API_KEY", None)
