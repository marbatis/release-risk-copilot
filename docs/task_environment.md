# Task Environment

## 1. Rational objective
Provide deterministic, inspectable release-risk decision support that helps engineering teams decide whether to proceed (`GO`), proceed carefully (`CAUTION`), or pause (`HOLD`) without handing decision authority to an LLM.

## 2. PEAS
- Performance measures
  - Correct deterministic decision output
  - Stable policy behavior across sample scenarios
  - Evidence coverage transparency
  - Fast local execution and reproducible test pass
- Environment
  - Release metadata JSON bundles
  - Local synthetic corpora (dependencies/incidents/ownership/runbooks/policies)
  - Optional OpenAI API for explanation only
- Actuators
  - API responses
  - Web UI rendering
  - Persisted assessment records
- Sensors
  - Bundle fields
  - Retrieved local evidence
  - Deterministic rule checks
  - Policy thresholds

## 3. Environmental dimensions
- Observability: partially observable; real production state is approximated by provided signals and local corpora.
- Determinism: deterministic core (rules, scoring, policy) with optional non-deterministic explanation layer.
- Episodic vs sequential: primarily episodic per assessment, with sequential value from persisted history.
- Static vs dynamic: dynamic in real use, but locally simulated with synthetic corpora.
- Discrete vs continuous: mostly discrete decisions with continuous risk score.

## 4. Problem formalization
Given a validated release bundle `B`, retrieved evidence `E`, and policy thresholds `T`, compute:
1. deterministic rule findings `R`
2. bounded risk score `S in [0,100]`
3. evidence coverage `C in [0,1]`
4. final decision `D in {GO, CAUTION, HOLD}`
subject to:
- hard blocks dominate (`D=HOLD`)
- policy thresholds determine base decision
- weak coverage downgrades one level
- explanation text cannot change `D`

## 5. Architecture choice
Workflow pipeline:
1. input validation (Pydantic)
2. deterministic retrieval (local corpora)
3. deterministic rules engine
4. deterministic risk scoring
5. deterministic coverage computation
6. deterministic policy decision
7. explanation provider (OpenAI or mock)
8. persistence (SQLite/SQLAlchemy)
9. API/Web presentation

This separation enforces "policy decides, model explains" and keeps behavior auditable.

## 6. Guardrails / workflow maturity
- No production actions.
- No auto-approval.
- No hidden model authority.
- `OPENAI_API_KEY` backend-only.
- Mock mode available with no key.
- Upload size limits and JSON object validation.
- Local evidence retrieval only (no arbitrary file reads).
- Reproducible tests and CI workflow.
