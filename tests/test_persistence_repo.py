"""Repository-level persistence tests."""

from app.providers.mock_provider import MockMemoProvider
from app.repositories.assessment_repo import AssessmentRepository
from app.services.assessment_service import AssessmentService
from app.services.decision_policy import DecisionPolicy
from app.services.rules_engine import RulesEngine
from app.services.sample_data import SampleDataRepository


def test_assessment_repository_save_and_get() -> None:
    repo = AssessmentRepository()
    sample_repo = SampleDataRepository()
    service = AssessmentService(
        rules_engine=RulesEngine(),
        policy=DecisionPolicy(),
        memo_provider=MockMemoProvider(),
    )

    assessment = service.assess(sample_repo.load_sample("go_clean_release"))
    repo.save(assessment)

    restored = repo.get_by_assessment_id(assessment.assessment_id)
    assert restored is not None
    assert restored.assessment_id == assessment.assessment_id
    assert restored.bundle.service == "billing-api"
