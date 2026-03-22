"""HTTP routes for MVP assessment workflow."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import ValidationError

from app.providers.mock_provider import MockMemoProvider
from app.schemas.models import Assessment, ReleaseBundle
from app.services.assessment_service import AssessmentService
from app.services.decision_policy import DecisionPolicy
from app.services.rules_engine import RulesEngine
from app.services.sample_data import SampleDataRepository

router = APIRouter()

_sample_repo = SampleDataRepository()
_default_sample_name = "go_clean_release"
_assessment_service = AssessmentService(
    rules_engine=RulesEngine(),
    policy=DecisionPolicy(),
    memo_provider=MockMemoProvider(),
)


@router.get("/health")
def health() -> dict[str, str]:
    """Basic liveness check."""

    return {"status": "ok", "provider_mode": "mock"}


@router.get("/samples")
def list_samples() -> dict[str, list[str]]:
    """List available local sample bundles."""

    return {"samples": _sample_repo.list_samples()}


@router.post("/assessments", response_model=Assessment)
def assess_release(bundle: ReleaseBundle) -> Assessment:
    """Run a deterministic assessment for a posted release bundle."""

    return _assessment_service.assess(bundle)


def _assess_sample_name(sample_name: str) -> Assessment:
    """Load one sample fixture and run deterministic assessment."""

    try:
        sample = _sample_repo.load_sample(sample_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, ValidationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _assessment_service.assess(sample)


@router.post("/assessments/sample", response_model=Assessment)
def assess_sample_default(
    sample_name: str = Query(
        default=_default_sample_name,
        description=(
            "Sample fixture name. Use GET /samples to list valid names. "
            "Default is go_clean_release."
        ),
        examples=["go_clean_release", "caution_elevated_risk", "hold_hard_block"],
    ),
) -> Assessment:
    """Run a deterministic assessment on a sample fixture with a default value."""

    return _assess_sample_name(sample_name)


@router.post("/assessments/sample/{sample_name}", response_model=Assessment)
def assess_sample(
    sample_name: str = Path(
        ...,
        description="Sample fixture name. Use GET /samples to list valid names.",
        examples=["go_clean_release", "caution_elevated_risk", "hold_hard_block"],
    ),
) -> Assessment:
    """Run a deterministic assessment on a bundled sample fixture."""

    return _assess_sample_name(sample_name)
