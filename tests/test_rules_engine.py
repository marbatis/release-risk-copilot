"""Rules engine behavior tests."""

from app.services.rules_engine import RulesEngine
from app.services.sample_data import SampleDataRepository


def test_rules_engine_reports_hard_blocks_for_hold_fixture() -> None:
    repo = SampleDataRepository()
    engine = RulesEngine()

    evaluation = engine.evaluate(repo.load_sample("hold_hard_block"))

    hard_block_ids = {item.rule_id for item in evaluation.hard_blocks}
    assert "freeze_active" in hard_block_ids
    assert "ci_failed" in hard_block_ids
    assert "dependency_down" in hard_block_ids


def test_rules_engine_reports_risk_flags_for_caution_fixture() -> None:
    repo = SampleDataRepository()
    engine = RulesEngine()

    evaluation = engine.evaluate(repo.load_sample("caution_elevated_risk"))

    assert not evaluation.hard_blocks
    assert evaluation.risk_score >= 35.0
    assert evaluation.evidence_coverage == 1.0
