"""Deterministic release-risk rules engine."""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from app.schemas.models import (
    CIStatus,
    DependencyHealth,
    FindingLevel,
    IncidentSeverity,
    IncidentStatus,
    ReleaseBundle,
    RetrievedEvidence,
    RuleCheck,
    RuleFinding,
    RulesEvaluation,
    RuleSeverity,
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

COVERAGE_CATEGORIES: tuple[str, ...] = (
    "bundle_core",
    "dependency_health",
    "incidents",
    "ownership",
    "runbook",
    "rollback",
    "approvals_ci",
)


class RulesEngine:
    """Run deterministic risk and hard-block checks over a release bundle."""

    def evaluate(
        self,
        bundle: ReleaseBundle,
        retrieved_evidence: Optional[list[RetrievedEvidence]] = None,
    ) -> RulesEvaluation:
        hard_blocks: list[RuleFinding] = []
        risk_flags: list[RuleFinding] = []
        rule_checks: list[RuleCheck] = []
        retrieved_evidence = retrieved_evidence or []

        missing_evidence = self._missing_evidence(bundle)
        coverage_by_category = self._coverage_by_category(bundle)
        evidence_coverage = round(
            sum(coverage_by_category.values()) / len(COVERAGE_CATEGORIES),
            3,
        )

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
            rule_checks.append(
                RuleCheck(
                    rule_name="change_freeze",
                    passed=False,
                    severity=RuleSeverity.HARD_BLOCK,
                    message="Change freeze is active.",
                )
            )
        else:
            rule_checks.append(
                RuleCheck(
                    rule_name="change_freeze",
                    passed=True,
                    severity=RuleSeverity.INFO,
                    message="No change freeze hard block detected.",
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
            rule_checks.append(
                RuleCheck(
                    rule_name="ci_pass_required",
                    passed=False,
                    severity=RuleSeverity.HARD_BLOCK,
                    message="CI failed for this release.",
                )
            )
        else:
            rule_checks.append(
                RuleCheck(
                    rule_name="ci_pass_required",
                    passed=True,
                    severity=RuleSeverity.INFO,
                    message="CI hard-block check passed.",
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
            rule_checks.append(
                RuleCheck(
                    rule_name="rollback_plan_required",
                    passed=False,
                    severity=RuleSeverity.HARD_BLOCK,
                    message="Rollback plan is required but missing.",
                )
            )
        else:
            rule_checks.append(
                RuleCheck(
                    rule_name="rollback_plan_required",
                    passed=True,
                    severity=RuleSeverity.INFO,
                    message="Rollback plan hard-block check passed.",
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
                        evidence=[f"down_dependencies={','.join(sorted(down_dependencies))}"],
                        weight=100.0,
                    )
                )
                rule_checks.append(
                    RuleCheck(
                        rule_name="dependency_down",
                        passed=False,
                        severity=RuleSeverity.HARD_BLOCK,
                        message="One or more dependencies are down.",
                    )
                )
            else:
                rule_checks.append(
                    RuleCheck(
                        rule_name="dependency_down",
                        passed=True,
                        severity=RuleSeverity.INFO,
                        message="No dependency-down hard block detected.",
                    )
                )

            if degraded_dependencies:
                risk_flags.append(
                    RuleFinding(
                        rule_id="dependency_degraded",
                        level=FindingLevel.RISK,
                        message="At least one required dependency is degraded.",
                        evidence=[f"degraded_dependencies={','.join(sorted(degraded_dependencies))}"],
                        weight=10.0,
                    )
                )
                rule_checks.append(
                    RuleCheck(
                        rule_name="dependency_degraded",
                        passed=False,
                        severity=RuleSeverity.WARNING,
                        message="One or more dependencies are degraded.",
                    )
                )
            else:
                rule_checks.append(
                    RuleCheck(
                        rule_name="dependency_degraded",
                        passed=True,
                        severity=RuleSeverity.INFO,
                        message="No degraded dependencies detected.",
                    )
                )

        if bundle.recent_incidents:
            service_incidents = [
                incident
                for incident in bundle.recent_incidents
                if incident.linked_service == bundle.service
            ]
            active_sev1 = [
                incident.incident_id
                for incident in service_incidents
                if incident.severity == IncidentSeverity.SEV1
                and incident.status in {IncidentStatus.OPEN, IncidentStatus.MITIGATED}
            ]
            active_sev2 = [
                incident.incident_id
                for incident in service_incidents
                if incident.severity == IncidentSeverity.SEV2
                and incident.status in {IncidentStatus.OPEN, IncidentStatus.MITIGATED}
            ]
            recent_sev2_resolved = [
                incident.incident_id
                for incident in service_incidents
                if incident.severity == IncidentSeverity.SEV2
                and incident.status == IncidentStatus.RESOLVED
                and (bundle.created_at - incident.started_at) <= timedelta(days=7)
            ]

            if active_sev1:
                hard_blocks.append(
                    RuleFinding(
                        rule_id="open_sev1_incident",
                        level=FindingLevel.HARD_BLOCK,
                        message="Active SEV1 incident linked to this service.",
                        evidence=[f"active_sev1={','.join(sorted(active_sev1))}"],
                        weight=100.0,
                    )
                )
                rule_checks.append(
                    RuleCheck(
                        rule_name="active_sev1",
                        passed=False,
                        severity=RuleSeverity.HARD_BLOCK,
                        message="Active SEV1 incident exists for this service.",
                    )
                )
            else:
                rule_checks.append(
                    RuleCheck(
                        rule_name="active_sev1",
                        passed=True,
                        severity=RuleSeverity.INFO,
                        message="No active SEV1 incident found.",
                    )
                )

            if active_sev2:
                risk_flags.append(
                    RuleFinding(
                        rule_id="open_sev2_incident",
                        level=FindingLevel.RISK,
                        message="Active SEV2 incident linked to this service.",
                        evidence=[f"active_sev2={','.join(sorted(active_sev2))}"],
                        weight=18.0,
                    )
                )

            if recent_sev2_resolved:
                risk_flags.append(
                    RuleFinding(
                        rule_id="recent_sev2_incident",
                        level=FindingLevel.RISK,
                        message="Recent SEV2 incident resolved within the last 7 days.",
                        evidence=[f"recent_sev2={','.join(sorted(recent_sev2_resolved))}"],
                        weight=8.0,
                    )
                )

            if active_sev2 or recent_sev2_resolved:
                rule_checks.append(
                    RuleCheck(
                        rule_name="recent_sev2",
                        passed=False,
                        severity=RuleSeverity.WARNING,
                        message="SEV2 incident activity is elevated for this service.",
                    )
                )
            else:
                rule_checks.append(
                    RuleCheck(
                        rule_name="recent_sev2",
                        passed=True,
                        severity=RuleSeverity.INFO,
                        message="No elevated recent SEV2 incident activity found.",
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
            rule_checks.append(
                RuleCheck(
                    rule_name="approvals_minimum",
                    passed=False,
                    severity=RuleSeverity.WARNING,
                    message="Approval count is below deterministic policy minimum.",
                )
            )
        else:
            rule_checks.append(
                RuleCheck(
                    rule_name="approvals_minimum",
                    passed=True,
                    severity=RuleSeverity.INFO,
                    message="Approval count check passed.",
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
            rule_checks.append(
                RuleCheck(
                    rule_name="flaky_tests",
                    passed=False,
                    severity=RuleSeverity.WARNING,
                    message="Flaky test count is elevated.",
                )
            )
        else:
            rule_checks.append(
                RuleCheck(
                    rule_name="flaky_tests",
                    passed=True,
                    severity=RuleSeverity.INFO,
                    message="Flaky test check passed.",
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
                rule_checks.append(
                    RuleCheck(
                        rule_name="oversized_diff",
                        passed=False,
                        severity=RuleSeverity.WARNING,
                        message="Diff size exceeds deterministic caution threshold.",
                    )
                )
            else:
                rule_checks.append(
                    RuleCheck(
                        rule_name="oversized_diff",
                        passed=True,
                        severity=RuleSeverity.INFO,
                        message="Diff size is within expected range.",
                    )
                )

        if bundle.runbook_link_present is False:
            risk_flags.append(
                RuleFinding(
                    rule_id="runbook_missing",
                    level=FindingLevel.RISK,
                    message="Runbook evidence is missing for this release.",
                    evidence=["runbook_link_present=false"],
                    weight=12.0,
                )
            )
            rule_checks.append(
                RuleCheck(
                    rule_name="runbook_present",
                    passed=False,
                    severity=RuleSeverity.WARNING,
                    message="Runbook evidence is missing.",
                )
            )
        else:
            rule_checks.append(
                RuleCheck(
                    rule_name="runbook_present",
                    passed=True,
                    severity=RuleSeverity.INFO,
                    message="Runbook evidence check passed.",
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

        if bundle.ownership is None:
            risk_flags.append(
                RuleFinding(
                    rule_id="ownership_missing",
                    level=FindingLevel.RISK,
                    message="Service ownership evidence is missing.",
                    evidence=["ownership=missing"],
                    weight=12.0,
                )
            )
            rule_checks.append(
                RuleCheck(
                    rule_name="ownership_present",
                    passed=False,
                    severity=RuleSeverity.WARNING,
                    message="Ownership information is missing.",
                )
            )
        else:
            rule_checks.append(
                RuleCheck(
                    rule_name="ownership_present",
                    passed=True,
                    severity=RuleSeverity.INFO,
                    message="Ownership evidence is present.",
                )
            )
            if not bundle.ownership.oncall_defined:
                risk_flags.append(
                    RuleFinding(
                        rule_id="oncall_missing",
                        level=FindingLevel.RISK,
                        message="Owning team has no explicit on-call assignment.",
                        evidence=[f"owning_team={bundle.ownership.owning_team}"],
                        weight=15.0,
                    )
                )

            if bundle.ownership.last_reviewed_at is None:
                risk_flags.append(
                    RuleFinding(
                        rule_id="ownership_review_missing",
                        level=FindingLevel.RISK,
                        message="Ownership review timestamp is missing.",
                        evidence=[f"service={bundle.ownership.service}"],
                        weight=8.0,
                    )
                )
            elif (bundle.created_at - bundle.ownership.last_reviewed_at) > timedelta(days=30):
                risk_flags.append(
                    RuleFinding(
                        rule_id="ownership_review_stale",
                        level=FindingLevel.RISK,
                        message="Ownership review is stale (older than 30 days).",
                        evidence=[f"last_reviewed_at={bundle.ownership.last_reviewed_at.isoformat()}"],
                        weight=8.0,
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

        rollback_readiness = self._rollback_readiness(bundle)
        risk_score = round(
            sum(item.weight for item in hard_blocks) + sum(item.weight for item in risk_flags),
            2,
        )

        return RulesEvaluation(
            hard_blocks=hard_blocks,
            risk_flags=risk_flags,
            rule_checks=rule_checks,
            retrieved_evidence=retrieved_evidence,
            missing_evidence=missing_evidence,
            evidence_checks=list(EVIDENCE_FIELDS),
            coverage_by_category=coverage_by_category,
            risk_score=risk_score,
            evidence_coverage=evidence_coverage,
            rollback_readiness=rollback_readiness,
        )

    @staticmethod
    def _missing_evidence(bundle: ReleaseBundle) -> list[str]:
        """Return required evidence fields that are currently missing."""

        missing: list[str] = []
        for field in EVIDENCE_FIELDS:
            if getattr(bundle, field) is None:
                missing.append(field)
        return missing

    @staticmethod
    def _coverage_by_category(bundle: ReleaseBundle) -> dict[str, float]:
        """Compute category-level evidence coverage values."""

        return {
            "bundle_core": 1.0,
            "dependency_health": 1.0 if bundle.dependencies else 0.0,
            "incidents": 1.0 if bundle.recent_incidents else 0.0,
            "ownership": 1.0 if bundle.ownership else 0.0,
            "runbook": 1.0 if bundle.runbook_link_present else 0.0,
            "rollback": 1.0 if bundle.rollback_plan_present else 0.0,
            "approvals_ci": (
                (1.0 if bundle.approvals is not None else 0.0)
                + (1.0 if bundle.ci_status is not None else 0.0)
            )
            / 2.0,
        }

    @staticmethod
    def _rollback_readiness(bundle: ReleaseBundle) -> str:
        if bundle.rollback_plan_present is True and bundle.runbook_link_present is True:
            return "ready"
        if bundle.rollback_plan_present is False:
            return "missing_rollback_plan"
        if bundle.runbook_link_present is False:
            return "runbook_missing"
        return "unknown"
