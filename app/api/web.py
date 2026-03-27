"""Server-rendered web routes for release risk demo."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.api.deps import assessment_repo, assessment_service, sample_repo, settings
from app.schemas.models import ReleaseBundle

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


def _render_error(request: Request, status_code: int, message: str) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={"status_code": status_code, "message": message},
        status_code=status_code,
    )


@router.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    """Render landing page with sample picker and upload form."""

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "samples": sample_repo.list_samples(),
            "default_sample": "go_clean_release",
        },
    )


@router.post("/assessments/run-sample")
def run_sample(sample_name: str = Form("go_clean_release")) -> RedirectResponse:
    """Run assessment against a named sample and redirect to detail view."""

    try:
        bundle = sample_repo.load_sample(sample_name)
    except (FileNotFoundError, ValidationError, ValueError):
        return RedirectResponse(url="/?error=invalid_sample", status_code=303)

    assessment = assessment_service.assess(bundle)
    return RedirectResponse(url=f"/assessments/{assessment.assessment_id}", status_code=303)


@router.post("/assessments/upload", response_model=None)
async def upload_assessment(
    request: Request,
    bundle_file: UploadFile = File(...),
) -> Response:
    """Parse uploaded release JSON, run assessment, and redirect to detail."""

    raw_bytes = await bundle_file.read(settings.upload_max_bytes + 1)
    if len(raw_bytes) > settings.upload_max_bytes:
        return _render_error(request, 413, f"Upload exceeds {settings.upload_max_bytes} byte limit.")

    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _render_error(request, 400, "Uploaded file is not valid UTF-8 JSON.")

    if not isinstance(payload, dict):
        return _render_error(request, 400, "Uploaded JSON must be an object.")

    try:
        bundle = ReleaseBundle.model_validate(payload)
    except ValidationError as exc:
        return _render_error(request, 422, f"Release bundle validation failed: {exc.errors()[0]['msg']}")

    assessment = assessment_service.assess(bundle)
    return RedirectResponse(url=f"/assessments/{assessment.assessment_id}", status_code=303)


@router.get("/history", response_class=HTMLResponse)
def history(
    request: Request,
    sort: str = "evaluated_at",
    order: str = "desc",
) -> HTMLResponse:
    """Render persisted assessment history."""

    rows = assessment_repo.list_history(limit=500)

    sortable: dict[str, Any] = {
        "evaluated_at": lambda row: row.evaluated_at,
        "risk_score": lambda row: row.risk_score,
        "decision": lambda row: row.decision,
        "service": lambda row: row.service,
    }
    sort_key = sortable.get(sort, sortable["evaluated_at"])
    reverse = order != "asc"
    rows = sorted(rows, key=sort_key, reverse=reverse)

    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={
            "rows": rows,
            "sort": sort,
            "order": order,
        },
    )


@router.get("/assessments/{assessment_id}", response_class=HTMLResponse)
def assessment_detail(request: Request, assessment_id: str) -> HTMLResponse:
    """Render persisted assessment detail page."""

    assessment = assessment_repo.get_by_assessment_id(assessment_id)
    if assessment is None:
        return _render_error(request, 404, f"Assessment not found: {assessment_id}")

    return templates.TemplateResponse(
        request=request,
        name="assessment_detail.html",
        context={
            "assessment": assessment,
            "decision": assessment.decision.decision.value,
            "risk_percent": min(100.0, max(0.0, assessment.rules.risk_score)),
        },
    )
