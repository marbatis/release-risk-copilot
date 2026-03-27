"""Deterministic local evidence retrieval tests."""

from app.schemas.models import EvidenceSourceType
from app.services.retrieval import RetrievalService
from app.services.sample_data import SampleDataRepository


def test_retrieval_returns_expected_evidence_sources_for_caution_sample() -> None:
    repo = SampleDataRepository()
    service = RetrievalService()

    result = service.retrieve(repo.load_sample("caution_elevated_risk"))

    source_types = {item.source_type for item in result.evidence}
    assert EvidenceSourceType.DEPENDENCY in source_types
    assert EvidenceSourceType.INCIDENT in source_types
    assert EvidenceSourceType.OWNERSHIP in source_types
    assert EvidenceSourceType.RUNBOOK in source_types
    assert EvidenceSourceType.POLICY in source_types


def test_retrieval_merges_missing_fields_when_possible() -> None:
    repo = SampleDataRepository()
    service = RetrievalService()

    bundle = repo.load_sample("go_clean_release").model_copy(
        update={"dependencies": None, "recent_incidents": None, "ownership": None}
    )
    result = service.retrieve(bundle)

    assert result.normalized_bundle.dependencies
    assert result.normalized_bundle.recent_incidents
    assert result.normalized_bundle.ownership is not None
