"""FastAPI route smoke tests for MVP foundation."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_assess_sample_endpoint_returns_decision() -> None:
    response = client.post("/assessments/sample/go_clean_release")

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"]["decision"] == "GO"
    assert payload["memo"]["provider_name"] == "mock"


def test_assess_sample_default_endpoint_uses_default_fixture() -> None:
    response = client.post("/assessments/sample")

    assert response.status_code == 200
    payload = response.json()
    assert payload["bundle"]["release_id"] == "REL-2026-0001"
    assert payload["decision"]["decision"] == "GO"


def test_assess_sample_default_endpoint_allows_query_override() -> None:
    response = client.post("/assessments/sample?sample_name=hold_hard_block")

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"]["decision"] == "HOLD"
