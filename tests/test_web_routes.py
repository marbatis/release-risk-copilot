"""Web route tests for server-rendered UI."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "upload_bundle.json"


def test_home_page_renders() -> None:
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "Deterministic release decision support" in response.text


def test_upload_endpoint_creates_assessment_and_redirects_to_detail() -> None:
    with TestClient(app) as client:
        payload = FIXTURE_PATH.read_bytes()
        response = client.post(
            "/assessments/upload",
            files={"bundle_file": ("upload_bundle.json", payload, "application/json")},
            follow_redirects=False,
        )

        assert response.status_code == 303
        detail_path = response.headers["location"]
        assert detail_path.startswith("/assessments/")

        detail_response = client.get(detail_path)
        assert detail_response.status_code == 200
        assert "Grounded Memo" in detail_response.text


def test_history_page_renders() -> None:
    with TestClient(app) as client:
        client.post("/assessments/sample/go_clean_release")
        response = client.get("/history")

        assert response.status_code == 200
        assert "Assessment History" in response.text


def test_upload_endpoint_rejects_oversized_payload() -> None:
    with TestClient(app) as client:
        payload = b"{" + (b"x" * 210000) + b"}"
        response = client.post(
            "/assessments/upload",
            files={"bundle_file": ("big.json", payload, "application/json")},
            follow_redirects=False,
        )

        assert response.status_code == 413
