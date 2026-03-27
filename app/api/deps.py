"""Shared app dependencies for API and web routes."""

from __future__ import annotations

from app.config import get_settings
from app.providers.factory import build_memo_provider
from app.repositories.assessment_repo import AssessmentRepository
from app.services.assessment_service import AssessmentService
from app.services.decision_policy import DecisionPolicy
from app.services.rules_engine import RulesEngine
from app.services.sample_data import SampleDataRepository

settings = get_settings()
sample_repo = SampleDataRepository()
assessment_repo = AssessmentRepository()
memo_provider = build_memo_provider(settings)
assessment_service = AssessmentService(
    rules_engine=RulesEngine(),
    policy=DecisionPolicy(),
    memo_provider=memo_provider,
    assessment_repo=assessment_repo,
)
