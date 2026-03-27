"""Orchestration service for release assessment workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.providers.base import MemoProvider
from app.repositories.assessment_repo import AssessmentRepository
from app.schemas.models import Assessment, ReleaseBundle
from app.services.decision_policy import DecisionPolicy
from app.services.retrieval import RetrievalService
from app.services.risk_scoring import RiskScoringService
from app.services.rules_engine import RulesEngine


class AssessmentService:
    """Run deterministic workflow: retrieval -> rules -> score -> policy -> memo."""

    def __init__(
        self,
        rules_engine: RulesEngine,
        policy: DecisionPolicy,
        memo_provider: MemoProvider,
        assessment_repo: Optional[AssessmentRepository] = None,
        retrieval_service: Optional[RetrievalService] = None,
        risk_scoring_service: Optional[RiskScoringService] = None,
    ) -> None:
        self.rules_engine = rules_engine
        self.policy = policy
        self.memo_provider = memo_provider
        self.assessment_repo = assessment_repo
        self.retrieval_service = retrieval_service or RetrievalService()
        self.risk_scoring_service = risk_scoring_service or RiskScoringService()

    def assess(self, bundle: ReleaseBundle) -> Assessment:
        """Produce a complete assessment artifact."""

        retrieval_result = self.retrieval_service.retrieve(bundle)
        normalized_bundle = retrieval_result.normalized_bundle

        evaluation = self.rules_engine.evaluate(
            normalized_bundle,
            retrieved_evidence=retrieval_result.evidence,
        )
        risk_score = self.risk_scoring_service.score(evaluation)
        evaluation = evaluation.model_copy(update={"risk_score": risk_score})

        decision = self.policy.decide(evaluation)
        if decision.downgraded_for_coverage:
            evaluation = evaluation.model_copy(update={"coverage_downgrade_reason": decision.rationale})

        memo = self.memo_provider.generate_memo(normalized_bundle, evaluation, decision)

        assessment = Assessment(
            assessment_id=f"asm_{uuid4().hex[:12]}",
            evaluated_at=datetime.now(timezone.utc),
            bundle=normalized_bundle,
            rules=evaluation,
            decision=decision,
            memo=memo,
            retrieved_evidence=retrieval_result.evidence,
        )
        if self.assessment_repo is not None:
            self.assessment_repo.save(assessment)
        return assessment
