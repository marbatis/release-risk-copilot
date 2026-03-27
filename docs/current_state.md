# Current MVP State (Baseline)

Last updated: 2026-03-27

## Current modules
- `app/main.py`
  - FastAPI app setup and root route.
- `app/api/routes.py`
  - API endpoints for health, samples, and assessment execution.
- `app/schemas/models.py`
  - Pydantic models for bundle input, rules output, policy output, and final assessment artifact.
- `app/services/sample_data.py`
  - Local sample bundle listing and loading from `data/sample_bundles/`.
- `app/services/rules_engine.py`
  - Deterministic risk/hard-block checks and evidence coverage calculation.
- `app/services/decision_policy.py`
  - Deterministic policy mapping rules output to `GO` / `CAUTION` / `HOLD`.
- `app/services/assessment_service.py`
  - Orchestration of rules -> policy -> memo provider.
- `app/providers/base.py`
  - Provider interface for memo generation.
- `app/providers/mock_provider.py`
  - Deterministic mock memo provider.

## Current routes
- `GET /`
- `GET /health`
- `GET /samples`
- `POST /assessments`
- `POST /assessments/sample`
- `POST /assessments/sample/{sample_name}`

## Current tests
- `tests/test_api.py`
  - Health route and sample assessment route behavior.
- `tests/test_rules_engine.py`
  - Hard-block and risk-flag behavior against fixtures.
- `tests/test_decision_policy.py`
  - Final decision outcomes against fixtures.
- `tests/test_sample_data.py`
  - Fixture listing/loading behavior.

Baseline status before v1 extension:
- Existing deterministic flow is working.
- Existing sample decisions are stable:
  - `go_clean_release` -> `GO`
  - `caution_elevated_risk` -> `CAUTION`
  - `hold_hard_block` -> `HOLD`
- Strict `commit_sha` validation already exists.

## Planned extensions from this baseline
- Add persistence (SQLite + SQLAlchemy) and history retrieval.
- Add deterministic local retrieval over incidents/dependencies/ownership/runbooks/policies corpora.
- Extend rules and evidence coverage logic while keeping deterministic policy authority.
- Add OpenAI memo provider with schema validation and deterministic fallback.
- Add server-rendered web UI (home, detail, history, upload).
- Expand tests, docs, notebooks, and CI polish.
