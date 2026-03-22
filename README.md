# Release Risk Copilot (MVP Foundation)

Policy-first release risk assessment with deterministic rules, evidence retrieval, and AI-generated explanations.

## Why this matters
- Reduces false-GO risk by making hard-block checks explicit and deterministic.
- Keeps humans in control of release decisions while improving preflight consistency.
- Creates auditable release assessments that can be reviewed, tested, and iterated safely.

Implemented in this phase:
- scaffolding (FastAPI app + module layout)
- strict Pydantic schemas
- sample release bundle data
- deterministic rules engine
- deterministic decision policy (`GO` / `CAUTION` / `HOLD`)
- mock memo provider behind a provider interface
- focused tests for schema/rules/policy/routes

Out of scope in this phase:
- live integrations (GitHub, Jira, Slack, etc.)
- real OpenAI provider calls
- advanced UI

## Tech choices
- Python 3.11
- FastAPI
- Pydantic v2
- pytest
- Heroku-ready `Procfile` + `runtime.txt`

## Run locally

```bash
cd release-risk-copilot
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for interactive API docs.

## Test

```bash
cd release-risk-copilot
source .venv/bin/activate
pytest
```

## MVP endpoints
- `GET /health`
- `GET /samples`
- `POST /assessments` (assess posted release bundle)
- `POST /assessments/sample` (assess a bundled fixture; defaults to `go_clean_release`)
- `POST /assessments/sample/{sample_name}` (assess bundled fixture)

## Project layout

```text
release-risk-copilot/
  app/
    api/routes.py
    providers/{base.py,mock_provider.py}
    schemas/models.py
    services/{sample_data.py,rules_engine.py,decision_policy.py,assessment_service.py}
    main.py
  data/sample_bundles/
  tests/
  Procfile
  runtime.txt
```

## Security notes
- `OPENAI_API_KEY` is not required in this phase.
- Do not commit secrets.
- The memo provider runs in deterministic mock mode only.
