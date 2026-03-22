"""Deterministic mock memo provider for MVP mode."""

from __future__ import annotations

from app.providers.base import MemoProvider
from app.schemas.models import PolicyDecision, ReleaseBundle, RiskMemo, RulesEvaluation


class MockMemoProvider(MemoProvider):
    """Create deterministic memos without calling external APIs."""

    name = "mock"

    def generate_memo(
        self,
        bundle: ReleaseBundle,
        evaluation: RulesEvaluation,
        decision: PolicyDecision,
    ) -> RiskMemo:
        findings = evaluation.hard_blocks or evaluation.risk_flags

        top_risks = [finding.message for finding in findings[:3]]
        if not top_risks:
            top_risks = ["No elevated deterministic risks were detected."]

        supporting_evidence: list[str] = []
        for finding in (evaluation.hard_blocks + evaluation.risk_flags)[:5]:
            evidence_detail = ", ".join(finding.evidence) if finding.evidence else "no evidence tags"
            supporting_evidence.append(f"{finding.rule_id}: {evidence_detail}")

        if not supporting_evidence:
            supporting_evidence = [
                f"release_id={bundle.release_id}",
                f"service={bundle.service}",
                "rules_engine=deterministic_pass",
            ]

        summary = f"Recommendation {decision.decision.value}. {decision.rationale}"

        return RiskMemo(
            summary=summary,
            top_risks=top_risks,
            missing_evidence=evaluation.missing_evidence,
            supporting_evidence=supporting_evidence,
            recommendation=decision.decision,
            provider_name=self.name,
            deterministic=True,
        )
