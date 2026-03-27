"""HTTP routes for MVP assessment workflow."""

from fastapi import APIRouter, Body, HTTPException, Path, Query, Request
from pydantic import ValidationError
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import (
    assessment_repo,
    assessment_service,
    memo_provider,
    sample_repo,
)
from app.schemas.models import Assessment, AssessmentHistoryItem, DecisionLabel, ReleaseBundle

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
_default_sample_name = "go_clean_release"


@router.get("/health")
def health() -> dict[str, str]:
    """Basic liveness check."""

    return {"status": "ok", "provider_mode": memo_provider.name}


@router.get("/samples")
def list_samples() -> dict[str, list[str]]:
    """List available local sample bundles."""

    return {"samples": sample_repo.list_samples()}


@router.post("/assessments", response_model=Assessment)
@limiter.limit("20/minute")
def assess_release(
    request: Request,
    bundle: ReleaseBundle = Body(
        ...,
        openapi_examples={
            "valid_release_bundle": {
                "summary": "Valid release bundle",
                "description": "Minimal fully-valid payload with strict commit SHA format.",
                "value": {
                    "release_id": "REL-2026-1001",
                    "service": "billing-api",
                    "environment": "production",
                    "created_at": "2026-03-22T10:00:00Z",
                    "commit_sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
                    "change_freeze_active": False,
                    "rollback_plan_present": True,
                    "runbook_link_present": True,
                    "ci_status": "pass",
                    "approvals": 2,
                    "tests_passed": 128,
                    "tests_failed": 0,
                    "flaky_tests_7d": 0,
                    "diff_size": 210,
                    "dependencies": [{"name": "postgres", "status": "healthy"}],
                    "recent_incidents": [],
                    "ownership": {
                        "service": "billing-api",
                        "owning_team": "payments-platform",
                        "oncall_defined": True,
                    },
                    "metadata": {"change_ticket": "CHG-11823"},
                },
            }
        },
    )
) -> Assessment:
    """Run a deterministic assessment for a posted release bundle."""

    return assessment_service.assess(bundle)


@router.get("/api/assessments/history", response_model=list[AssessmentHistoryItem])
def list_assessment_history(limit: int = Query(default=100, ge=1, le=500)) -> list[AssessmentHistoryItem]:
    """Return persisted assessment summaries, newest first."""

    rows = assessment_repo.list_history(limit=limit)
    return [
        AssessmentHistoryItem(
            assessment_id=row.assessment_id,
            release_id=row.release_id,
            service=row.service,
            environment=row.environment,
            created_at=row.created_at,
            evaluated_at=row.evaluated_at,
            decision=DecisionLabel(row.decision),
            risk_score=row.risk_score,
        )
        for row in rows
    ]


@router.get("/api/assessments/{assessment_id}", response_model=Assessment)
def get_api_assessment_by_id(assessment_id: str = Path(..., min_length=1)) -> Assessment:
    """Return a previously persisted assessment by id."""

    assessment = assessment_repo.get_by_assessment_id(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail=f"Assessment not found: {assessment_id}")
    return assessment


def _assess_sample_name(sample_name: str) -> Assessment:
    """Load one sample fixture and run deterministic assessment."""

    try:
        sample = sample_repo.load_sample(sample_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, ValidationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return assessment_service.assess(sample)


@router.post("/assessments/sample", response_model=Assessment)
@limiter.limit("20/minute")
def assess_sample_default(
    request: Request,
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
@limiter.limit("20/minute")
def assess_sample(
    request: Request,
    sample_name: str = Path(
        ...,
        description="Sample fixture name. Use GET /samples to list valid names.",
        examples=["go_clean_release", "caution_elevated_risk", "hold_hard_block"],
    ),
) -> Assessment:
    """Run a deterministic assessment on a bundled sample fixture."""

    return _assess_sample_name(sample_name)
