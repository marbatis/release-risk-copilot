"""Decision policy coverage downgrade behavior tests."""

from app.schemas.models import RulesEvaluation
from app.services.decision_policy import DecisionPolicy


def test_policy_downgrades_go_to_caution_when_coverage_is_weak() -> None:
    policy = DecisionPolicy()
    evaluation = RulesEvaluation(risk_score=10.0, evidence_coverage=0.6)

    decision = policy.decide(evaluation)

    assert decision.base_decision.value == "GO"
    assert decision.decision.value == "CAUTION"
    assert decision.downgraded_for_coverage is True


def test_policy_downgrades_caution_to_hold_when_coverage_is_weak() -> None:
    policy = DecisionPolicy()
    evaluation = RulesEvaluation(risk_score=50.0, evidence_coverage=0.6)

    decision = policy.decide(evaluation)

    assert decision.base_decision.value == "CAUTION"
    assert decision.decision.value == "HOLD"
    assert decision.downgraded_for_coverage is True
