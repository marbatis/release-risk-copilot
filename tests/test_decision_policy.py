"""Decision policy integration tests against sample fixtures."""

from app.schemas.models import DecisionLabel
from app.services.decision_policy import DecisionPolicy
from app.services.rules_engine import RulesEngine
from app.services.sample_data import SampleDataRepository


def test_policy_go_for_low_risk_fixture() -> None:
    repo = SampleDataRepository()
    engine = RulesEngine()
    policy = DecisionPolicy()

    evaluation = engine.evaluate(repo.load_sample("go_clean_release"))
    decision = policy.decide(evaluation)

    assert decision.decision == DecisionLabel.GO


def test_policy_caution_for_elevated_risk_fixture() -> None:
    repo = SampleDataRepository()
    engine = RulesEngine()
    policy = DecisionPolicy()

    evaluation = engine.evaluate(repo.load_sample("caution_elevated_risk"))
    decision = policy.decide(evaluation)

    assert decision.decision == DecisionLabel.CAUTION


def test_policy_hold_for_hard_block_fixture() -> None:
    repo = SampleDataRepository()
    engine = RulesEngine()
    policy = DecisionPolicy()

    evaluation = engine.evaluate(repo.load_sample("hold_hard_block"))
    decision = policy.decide(evaluation)

    assert decision.decision == DecisionLabel.HOLD
