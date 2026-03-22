"""Orchestration service for release assessment workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.providers.base import MemoProvider
from app.schemas.models import Assessment, ReleaseBundle
from app.services.decision_policy import DecisionPolicy
from app.services.rules_engine import RulesEngine


class AssessmentService:
    """Run deterministic workflow: rules -> policy -> memo."""

    def __init__(
        self,
        rules_engine: RulesEngine,
        policy: DecisionPolicy,
        memo_provider: MemoProvider,
    ) -> None:
        self.rules_engine = rules_engine
        self.policy = policy
        self.memo_provider = memo_provider

    def assess(self, bundle: ReleaseBundle) -> Assessment:
        """Produce a complete assessment artifact."""

        evaluation = self.rules_engine.evaluate(bundle)
        decision = self.policy.decide(evaluation)
        memo = self.memo_provider.generate_memo(bundle, evaluation, decision)

        return Assessment(
            assessment_id=f"asm_{uuid4().hex[:12]}",
            evaluated_at=datetime.now(timezone.utc),
            bundle=bundle,
            rules=evaluation,
            decision=decision,
            memo=memo,
        )
