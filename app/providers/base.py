"""Provider abstraction for risk memo generation."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.models import PolicyDecision, ReleaseBundle, RiskMemo, RulesEvaluation


class MemoProvider(ABC):
    """Stable interface for memo generation backends."""

    name = "base"

    @abstractmethod
    def generate_memo(
        self,
        bundle: ReleaseBundle,
        evaluation: RulesEvaluation,
        decision: PolicyDecision,
    ) -> RiskMemo:
        """Build a structured memo from deterministic evaluation results."""
