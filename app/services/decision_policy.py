"""Deterministic policy that maps rules output to GO/CAUTION/HOLD."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml

from app.schemas.models import DecisionLabel, PolicyConfig, PolicyDecision, RulesEvaluation

DEFAULT_POLICY_FILE = Path(__file__).resolve().parents[2] / "data" / "policies" / "risk_policy.yaml"


class DecisionPolicy:
    """Apply deterministic policy thresholds to produce a final recommendation."""

    def __init__(self, config: Optional[PolicyConfig] = None, policy_file: Path = DEFAULT_POLICY_FILE) -> None:
        self.config = config or self._load_config(policy_file)

    def decide(self, evaluation: RulesEvaluation) -> PolicyDecision:
        """Decide GO/CAUTION/HOLD using deterministic order of precedence."""

        base_decision = self._base_decision(evaluation)

        if evaluation.evidence_coverage < self.config.go_min_coverage and base_decision != DecisionLabel.HOLD:
            downgraded = self._downgrade(base_decision)
            return PolicyDecision(
                decision=downgraded,
                rationale=(
                    f"Evidence coverage {evaluation.evidence_coverage:.0%} is below "
                    f"policy minimum {self.config.go_min_coverage:.0%}; "
                    f"downgraded from {base_decision.value} to {downgraded.value}."
                ),
                triggered_conditions=["coverage_downgrade"],
                policy_version=self.config.policy_version,
                downgraded_for_coverage=True,
                base_decision=base_decision,
            )

        return PolicyDecision(
            decision=base_decision,
            rationale=self._base_rationale(base_decision, evaluation),
            triggered_conditions=self._base_triggers(base_decision, evaluation),
            policy_version=self.config.policy_version,
            downgraded_for_coverage=False,
            base_decision=base_decision,
        )

    def _base_decision(self, evaluation: RulesEvaluation) -> DecisionLabel:
        if evaluation.hard_blocks:
            return DecisionLabel.HOLD

        if evaluation.risk_score >= self.config.hold_score_threshold:
            return DecisionLabel.HOLD

        if evaluation.risk_score >= self.config.caution_score_threshold:
            return DecisionLabel.CAUTION

        return DecisionLabel.GO

    def _base_rationale(self, decision: DecisionLabel, evaluation: RulesEvaluation) -> str:
        if decision == DecisionLabel.HOLD and evaluation.hard_blocks:
            return "One or more hard-block conditions are active."

        if decision == DecisionLabel.HOLD:
            return (
                f"Risk score {evaluation.risk_score:.1f} meets or exceeds "
                f"HOLD threshold {self.config.hold_score_threshold:.1f}."
            )

        if decision == DecisionLabel.CAUTION:
            return (
                f"Risk score {evaluation.risk_score:.1f} meets or exceeds "
                f"CAUTION threshold {self.config.caution_score_threshold:.1f}."
            )

        return "No hard blocks found and risk is below policy thresholds."

    @staticmethod
    def _base_triggers(decision: DecisionLabel, evaluation: RulesEvaluation) -> list[str]:
        if decision == DecisionLabel.HOLD and evaluation.hard_blocks:
            return [item.rule_id for item in evaluation.hard_blocks]
        if decision == DecisionLabel.HOLD:
            return ["risk_score_hold_threshold"]
        if decision == DecisionLabel.CAUTION:
            return ["risk_score_caution_threshold"]
        return ["policy_pass"]

    @staticmethod
    def _downgrade(decision: DecisionLabel) -> DecisionLabel:
        if decision == DecisionLabel.GO:
            return DecisionLabel.CAUTION
        if decision == DecisionLabel.CAUTION:
            return DecisionLabel.HOLD
        return DecisionLabel.HOLD

    @staticmethod
    def _load_config(policy_file: Path) -> PolicyConfig:
        """Load policy thresholds from YAML with safe deterministic defaults."""

        if not policy_file.exists():
            return PolicyConfig()

        raw: dict[str, Any] = yaml.safe_load(policy_file.read_text(encoding="utf-8")) or {}
        thresholds = raw.get("thresholds", {}) if isinstance(raw, dict) else {}

        return PolicyConfig(
            policy_version=str(raw.get("policy_version", "mvp-v1")),
            caution_score_threshold=float(
                thresholds.get("caution_score_threshold", PolicyConfig().caution_score_threshold)
            ),
            hold_score_threshold=float(
                thresholds.get("hold_score_threshold", PolicyConfig().hold_score_threshold)
            ),
            go_min_coverage=float(thresholds.get("go_min_coverage", PolicyConfig().go_min_coverage)),
            hold_min_coverage=float(thresholds.get("hold_min_coverage", PolicyConfig().hold_min_coverage)),
        )
