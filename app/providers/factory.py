"""Memo provider selection utilities."""

from __future__ import annotations

from app.config import Settings
from app.providers.base import MemoProvider
from app.providers.mock_provider import MockMemoProvider
from app.providers.openai_provider import OpenAIMemoProvider


def build_memo_provider(settings: Settings) -> MemoProvider:
    """Return OpenAI provider when key is present, otherwise deterministic mock."""

    if settings.openai_api_key:
        return OpenAIMemoProvider(api_key=settings.openai_api_key, model=settings.openai_model)
    return MockMemoProvider()
