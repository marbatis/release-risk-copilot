# Build Notes

## Major implementation decisions
- Preserved MVP API contract and sample decision outcomes as non-negotiable invariants.
- Introduced SQLAlchemy persistence with a simple `assessments` table to keep Heroku deployment straightforward.
- Kept deterministic core explicit by splitting retrieval, rules, risk scoring, and decision policy into separate services.
- Added category-level evidence coverage and one-level downgrade logic in policy for weak evidence.
- Kept model output bounded to memo generation only through provider abstraction.

## Provider strategy
- `MockMemoProvider` remains default and deterministic.
- `OpenAIMemoProvider` is backend-only and optional.
- OpenAI output is schema-validated; any failure falls back to deterministic mock memo.

## API and web surface
- Existing API endpoints retained:
  - `GET /health`
  - `GET /samples`
  - `POST /assessments`
- Added API persistence endpoints:
  - `GET /api/assessments/history`
  - `GET /api/assessments/{assessment_id}`
- Added web routes:
  - `GET /`
  - `GET /history`
  - `GET /assessments/{assessment_id}`
  - `POST /assessments/run-sample`
  - `POST /assessments/upload`

## Security and operational notes
- `OPENAI_API_KEY` is never exposed client-side.
- Upload endpoint enforces size and payload-shape checks.
- Startup initializes DB and logs provider mode without logging secrets.

## Testing approach
- Existing MVP tests kept and passing.
- Added tests for persistence, retrieval, coverage downgrade, OpenAI fallback, web routes, and OpenAPI example validity.
- Test execution uses `PYTHONPATH=.` and local SQLite test DB via `tests/conftest.py`.
