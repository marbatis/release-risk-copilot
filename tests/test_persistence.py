"""Persistence API tests."""

from fastapi.testclient import TestClient

from app.main import app


def test_assessment_is_saved_and_retrievable_via_api() -> None:
    with TestClient(app) as client:
        post_response = client.post("/assessments/sample/go_clean_release")
        assert post_response.status_code == 200
        assessment_id = post_response.json()["assessment_id"]

        history_response = client.get("/api/assessments/history")
        assert history_response.status_code == 200
        history_payload = history_response.json()
        assert any(row["assessment_id"] == assessment_id for row in history_payload)

        detail_response = client.get(f"/api/assessments/{assessment_id}")
        assert detail_response.status_code == 200
        detail_payload = detail_response.json()
        assert detail_payload["assessment_id"] == assessment_id
        assert detail_payload["bundle"]["release_id"] == "REL-2026-0001"
