"""Deterministic policy that maps rules output to GO/CAUTION/HOLD."""

from __future__ import annotations

from typing import Optional

from app.schemas.models import DecisionLabel, PolicyConfig, PolicyDecision, RulesEvaluation


class DecisionPolicy:
    """Apply deterministic policy thresholds to produce a final recommendation."""

    def __init__(self, config: Optional[PolicyConfig] = None) -> None:
        self.config = config or PolicyConfig()

    def decide(self, evaluation: RulesEvaluation) -> PolicyDecision:
        """Decide GO/CAUTION/HOLD using deterministic order of precedence."""

        if evaluation.hard_blocks:
            return PolicyDecision(
                decision=DecisionLabel.HOLD,
                rationale="One or more hard-block conditions are active.",
                triggered_conditions=[item.rule_id for item in evaluation.hard_blocks],
                policy_version=self.config.policy_version,
            )

        if evaluation.evidence_coverage < self.config.hold_min_coverage:
            return PolicyDecision(
                decision=DecisionLabel.HOLD,
                rationale=(
                    f"Evidence coverage {evaluation.evidence_coverage:.0%} is below "
                    f"the HOLD threshold {self.config.hold_min_coverage:.0%}."
                ),
                triggered_conditions=["coverage_below_hold_min"],
                policy_version=self.config.policy_version,
            )

        if evaluation.risk_score >= self.config.hold_score_threshold:
            return PolicyDecision(
                decision=DecisionLabel.HOLD,
                rationale=(
                    f"Risk score {evaluation.risk_score:.1f} meets or exceeds "
                    f"HOLD threshold {self.config.hold_score_threshold:.1f}."
                ),
                triggered_conditions=["risk_score_hold_threshold"],
                policy_version=self.config.policy_version,
            )

        if evaluation.evidence_coverage < self.config.go_min_coverage:
            return PolicyDecision(
                decision=DecisionLabel.CAUTION,
                rationale=(
                    f"Evidence coverage {evaluation.evidence_coverage:.0%} is below "
                    f"GO threshold {self.config.go_min_coverage:.0%}."
                ),
                triggered_conditions=["coverage_below_go_min"],
                policy_version=self.config.policy_version,
            )

        if evaluation.risk_score >= self.config.caution_score_threshold:
            return PolicyDecision(
                decision=DecisionLabel.CAUTION,
                rationale=(
                    f"Risk score {evaluation.risk_score:.1f} meets or exceeds "
                    f"CAUTION threshold {self.config.caution_score_threshold:.1f}."
                ),
                triggered_conditions=["risk_score_caution_threshold"],
                policy_version=self.config.policy_version,
            )

        return PolicyDecision(
            decision=DecisionLabel.GO,
            rationale="No hard blocks found and risk is below policy thresholds.",
            triggered_conditions=["policy_pass"],
            policy_version=self.config.policy_version,
        )
