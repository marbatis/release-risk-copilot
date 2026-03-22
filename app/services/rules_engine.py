"""Deterministic release-risk rules engine."""

from __future__ import annotations

from app.schemas.models import (
    CIStatus,
    DependencyHealth,
    FindingLevel,
    IncidentSeverity,
    IncidentStatus,
    ReleaseBundle,
    RuleFinding,
    RulesEvaluation,
)

EVIDENCE_FIELDS: tuple[str, ...] = (
    "change_freeze_active",
    "ci_status",
    "rollback_plan_present",
    "runbook_link_present",
    "dependencies",
    "recent_incidents",
    "ownership",
    "approvals",
    "flaky_tests_7d",
    "diff_size",
)


class RulesEngine:
    """Run deterministic risk and hard-block checks over a release bundle."""

    def evaluate(self, bundle: ReleaseBundle) -> RulesEvaluation:
        hard_blocks: list[RuleFinding] = []
        risk_flags: list[RuleFinding] = []

        missing_evidence = self._missing_evidence(bundle)
        evidence_coverage = (len(EVIDENCE_FIELDS) - len(missing_evidence)) / len(EVIDENCE_FIELDS)

        if bundle.change_freeze_active is True:
            hard_blocks.append(
                RuleFinding(
                    rule_id="freeze_active",
                    level=FindingLevel.HARD_BLOCK,
                    message="Change freeze is active for this release window.",
                    evidence=["change_freeze_active=true"],
                    weight=100.0,
                )
            )

        if bundle.ci_status == CIStatus.FAIL:
            hard_blocks.append(
                RuleFinding(
                    rule_id="ci_failed",
                    level=FindingLevel.HARD_BLOCK,
                    message="CI status failed.",
                    evidence=["ci_status=fail"],
                    weight=100.0,
                )
            )

        if bundle.rollback_plan_present is False:
            hard_blocks.append(
                RuleFinding(
                    rule_id="rollback_missing",
                    level=FindingLevel.HARD_BLOCK,
                    message="Rollback plan is missing.",
                    evidence=["rollback_plan_present=false"],
                    weight=100.0,
                )
            )

        if bundle.dependencies:
            down_dependencies = [dep.name for dep in bundle.dependencies if dep.status == DependencyHealth.DOWN]
            degraded_dependencies = [
                dep.name for dep in bundle.dependencies if dep.status == DependencyHealth.DEGRADED
            ]

            if down_dependencies:
                hard_blocks.append(
                    RuleFinding(
                        rule_id="dependency_down",
                        level=FindingLevel.HARD_BLOCK,
                        message="At least one required dependency is down.",
                        evidence=[f"down_dependencies={','.join(down_dependencies)}"],
                        weight=100.0,
                    )
                )

            if degraded_dependencies:
                risk_flags.append(
                    RuleFinding(
                        rule_id="dependency_degraded",
                        level=FindingLevel.RISK,
                        message="At least one required dependency is degraded.",
                        evidence=[f"degraded_dependencies={','.join(degraded_dependencies)}"],
                        weight=10.0,
                    )
                )

        if bundle.recent_incidents:
            open_sev1 = [
                incident.incident_id
                for incident in bundle.recent_incidents
                if incident.severity == IncidentSeverity.SEV1 and incident.status == IncidentStatus.OPEN
            ]
            open_sev2 = [
                incident.incident_id
                for incident in bundle.recent_incidents
                if incident.severity == IncidentSeverity.SEV2 and incident.status == IncidentStatus.OPEN
            ]

            if open_sev1:
                hard_blocks.append(
                    RuleFinding(
                        rule_id="open_sev1_incident",
                        level=FindingLevel.HARD_BLOCK,
                        message="Open SEV1 incident linked to release context.",
                        evidence=[f"open_sev1={','.join(open_sev1)}"],
                        weight=100.0,
                    )
                )

            if open_sev2:
                risk_flags.append(
                    RuleFinding(
                        rule_id="open_sev2_incident",
                        level=FindingLevel.RISK,
                        message="Open SEV2 incident linked to release context.",
                        evidence=[f"open_sev2={','.join(open_sev2)}"],
                        weight=18.0,
                    )
                )

        if bundle.flaky_tests_7d is not None and bundle.flaky_tests_7d >= 3:
            flaky_weight = 18.0 if bundle.flaky_tests_7d >= 6 else 12.0
            risk_flags.append(
                RuleFinding(
                    rule_id="flaky_tests",
                    level=FindingLevel.RISK,
                    message="Flaky test count in the last 7 days is elevated.",
                    evidence=[f"flaky_tests_7d={bundle.flaky_tests_7d}"],
                    weight=flaky_weight,
                )
            )

        if bundle.diff_size is not None:
            if bundle.diff_size >= 1000:
                diff_weight = 28.0
            elif bundle.diff_size >= 600:
                diff_weight = 18.0
            elif bundle.diff_size >= 350:
                diff_weight = 10.0
            else:
                diff_weight = 0.0

            if diff_weight > 0:
                risk_flags.append(
                    RuleFinding(
                        rule_id="large_diff",
                        level=FindingLevel.RISK,
                        message="Large change set increases rollback and verification risk.",
                        evidence=[f"diff_size={bundle.diff_size}"],
                        weight=diff_weight,
                    )
                )

        if bundle.approvals is not None and bundle.approvals < 2:
            risk_flags.append(
                RuleFinding(
                    rule_id="approvals_low",
                    level=FindingLevel.RISK,
                    message="Approval count is below the recommended minimum of 2.",
                    evidence=[f"approvals={bundle.approvals}"],
                    weight=12.0,
                )
            )

        if bundle.runbook_link_present is False:
            risk_flags.append(
                RuleFinding(
                    rule_id="runbook_missing",
                    level=FindingLevel.RISK,
                    message="Runbook link is missing for this release.",
                    evidence=["runbook_link_present=false"],
                    weight=12.0,
                )
            )

        if bundle.ci_status == CIStatus.UNKNOWN:
            risk_flags.append(
                RuleFinding(
                    rule_id="ci_unknown",
                    level=FindingLevel.RISK,
                    message="CI status is unknown.",
                    evidence=["ci_status=unknown"],
                    weight=15.0,
                )
            )

        if bundle.ownership and not bundle.ownership.oncall_defined:
            risk_flags.append(
                RuleFinding(
                    rule_id="oncall_missing",
                    level=FindingLevel.RISK,
                    message="Owning team has no explicit on-call assignment.",
                    evidence=[f"owning_team={bundle.ownership.owning_team}"],
                    weight=15.0,
                )
            )

        if missing_evidence:
            risk_flags.append(
                RuleFinding(
                    rule_id="missing_evidence",
                    level=FindingLevel.RISK,
                    message="Required evidence fields are missing.",
                    evidence=missing_evidence,
                    weight=min(len(missing_evidence) * 5.0, 25.0),
                )
            )

        risk_score = round(
            sum(item.weight for item in hard_blocks) + sum(item.weight for item in risk_flags),
            2,
        )

        return RulesEvaluation(
            hard_blocks=hard_blocks,
            risk_flags=risk_flags,
            missing_evidence=missing_evidence,
            evidence_checks=list(EVIDENCE_FIELDS),
            risk_score=risk_score,
            evidence_coverage=round(evidence_coverage, 3),
        )

    @staticmethod
    def _missing_evidence(bundle: ReleaseBundle) -> list[str]:
        """Return required evidence fields that are currently missing."""

        missing: list[str] = []
        for field in EVIDENCE_FIELDS:
            if getattr(bundle, field) is None:
                missing.append(field)
        return missing
