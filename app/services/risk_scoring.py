"""Deterministic risk scoring logic."""

from __future__ import annotations

from app.schemas.models import RulesEvaluation


class RiskScoringService:
    """Compute bounded risk score from deterministic rule findings."""

    def score(self, evaluation: RulesEvaluation) -> float:
        raw_score = sum(item.weight for item in evaluation.hard_blocks)
        raw_score += sum(item.weight for item in evaluation.risk_flags)
        return round(max(0.0, min(raw_score, 100.0)), 2)
