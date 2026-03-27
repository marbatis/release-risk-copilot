"""OpenAPI schema example validity tests."""

import re

from fastapi.testclient import TestClient

from app.main import app


def test_openapi_assessments_example_uses_valid_commit_sha_and_executes() -> None:
    with TestClient(app) as client:
        openapi = client.get("/openapi.json")
        assert openapi.status_code == 200

        schema = openapi.json()
        examples = schema["paths"]["/assessments"]["post"]["requestBody"]["content"]["application/json"]["examples"]
        payload = examples["valid_release_bundle"]["value"]

        assert re.fullmatch(r"[0-9a-fA-F]{7,40}", payload["commit_sha"]) is not None

        response = client.post("/assessments", json=payload)
        assert response.status_code == 200
        assert response.json()["decision"]["decision"] in {"GO", "CAUTION", "HOLD"}


def test_health_reports_mock_mode_without_openai_key() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["provider_mode"] == "mock"
