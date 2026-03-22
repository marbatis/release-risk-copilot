"""Sample data loader tests."""

from app.services.sample_data import SampleDataRepository


def test_list_samples_contains_expected_fixtures() -> None:
    repo = SampleDataRepository()

    samples = repo.list_samples()

    assert "go_clean_release" in samples
    assert "caution_elevated_risk" in samples
    assert "hold_hard_block" in samples


def test_load_sample_returns_release_bundle() -> None:
    repo = SampleDataRepository()

    bundle = repo.load_sample("go_clean_release")

    assert bundle.release_id == "REL-2026-0001"
    assert bundle.service == "billing-api"
