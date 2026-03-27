"""Core data models for Release Risk Copilot MVP."""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DecisionLabel(str, Enum):
    """Final release recommendation."""

    GO = "GO"
    CAUTION = "CAUTION"
    HOLD = "HOLD"


class CIStatus(str, Enum):
    """CI state provided with the release bundle."""

    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


class DependencyHealth(str, Enum):
    """Dependency operational state."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


class IncidentSeverity(str, Enum):
    """Incident severity scale."""

    SEV1 = "SEV1"
    SEV2 = "SEV2"
    SEV3 = "SEV3"


class IncidentStatus(str, Enum):
    """Lifecycle stage for an incident."""

    OPEN = "open"
    MITIGATED = "mitigated"
    RESOLVED = "resolved"


class FindingLevel(str, Enum):
    """Rule finding type."""

    HARD_BLOCK = "hard_block"
    RISK = "risk"


class RuleSeverity(str, Enum):
    """Human-readable severity level for rule checks."""

    INFO = "info"
    WARNING = "warning"
    HARD_BLOCK = "hard_block"


class EvidenceSourceType(str, Enum):
    """Supported local evidence source categories."""

    DEPENDENCY = "dependency"
    INCIDENT = "incident"
    OWNERSHIP = "ownership"
    RUNBOOK = "runbook"
    POLICY = "policy"
    BUNDLE = "bundle"


class ServiceOwnership(BaseModel):
    """Service owner and on-call metadata."""

    model_config = ConfigDict(extra="forbid")

    service: str = Field(min_length=1)
    owning_team: str = Field(min_length=1)
    oncall_defined: bool = True
    last_reviewed_at: Optional[datetime] = None


class DependencySignal(BaseModel):
    """Dependency health signal used by rules."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    status: DependencyHealth
    last_updated_at: Optional[datetime] = None


class IncidentSignal(BaseModel):
    """Recent incident record attached to the release."""

    model_config = ConfigDict(extra="forbid")

    incident_id: str = Field(min_length=1)
    severity: IncidentSeverity
    status: IncidentStatus
    linked_service: str = Field(min_length=1)
    started_at: datetime
    ended_at: Optional[datetime] = None


class ReleaseBundle(BaseModel):
    """Input payload for one release assessment."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "release_id": "REL-2026-1001",
                    "service": "billing-api",
                    "environment": "production",
                    "created_at": "2026-03-22T10:00:00Z",
                    "commit_sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
                    "change_freeze_active": False,
                    "rollback_plan_present": True,
                    "runbook_link_present": True,
                    "ci_status": "pass",
                    "approvals": 2,
                    "tests_passed": 120,
                    "tests_failed": 0,
                    "flaky_tests_7d": 1,
                    "diff_size": 240,
                    "dependencies": [
                        {"name": "postgres", "status": "healthy"},
                        {"name": "redis", "status": "healthy"},
                    ],
                    "recent_incidents": [],
                    "ownership": {
                        "service": "billing-api",
                        "owning_team": "payments-platform",
                        "oncall_defined": True,
                    },
                    "metadata": {"change_ticket": "CHG-12001"},
                }
            ]
        },
    )

    release_id: str = Field(min_length=1)
    service: str = Field(min_length=1)
    environment: str = Field(default="production", min_length=1)
    created_at: datetime
    commit_sha: str

    change_freeze_active: Optional[bool] = None
    rollback_plan_present: Optional[bool] = None
    runbook_link_present: Optional[bool] = None
    ci_status: Optional[CIStatus] = None

    approvals: Optional[int] = Field(default=None, ge=0)
    tests_passed: Optional[int] = Field(default=None, ge=0)
    tests_failed: Optional[int] = Field(default=None, ge=0)
    flaky_tests_7d: Optional[int] = Field(default=None, ge=0)
    diff_size: Optional[int] = Field(default=None, ge=0)

    dependencies: Optional[list[DependencySignal]] = None
    recent_incidents: Optional[list[IncidentSignal]] = None
    ownership: Optional[ServiceOwnership] = None

    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("commit_sha")
    @classmethod
    def validate_commit_sha(cls, value: str) -> str:
        """Accept short and long Git SHAs only."""

        if not re.fullmatch(r"[0-9a-fA-F]{7,40}", value):
            raise ValueError("commit_sha must be a 7-40 character hex git SHA")
        return value


class RuleFinding(BaseModel):
    """Single deterministic rule outcome."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(min_length=1)
    level: FindingLevel
    message: str = Field(min_length=1)
    evidence: list[str] = Field(default_factory=list)
    weight: float = Field(default=0.0, ge=0.0)


class RuleCheck(BaseModel):
    """Detailed pass/fail record for one deterministic rule."""

    model_config = ConfigDict(extra="forbid")

    rule_name: str = Field(min_length=1)
    passed: bool
    severity: RuleSeverity
    message: str = Field(min_length=1)


class RetrievedEvidence(BaseModel):
    """Single retrieved local evidence record."""

    model_config = ConfigDict(extra="forbid")

    source_type: EvidenceSourceType
    source_name: str = Field(min_length=1)
    excerpt: str = Field(min_length=1)
    relevance_score: float = Field(ge=0.0, le=1.0)
    source_ref: Optional[str] = None


class RulesEvaluation(BaseModel):
    """Aggregated output from the deterministic rules engine."""

    model_config = ConfigDict(extra="forbid")

    hard_blocks: list[RuleFinding] = Field(default_factory=list)
    risk_flags: list[RuleFinding] = Field(default_factory=list)
    rule_checks: list[RuleCheck] = Field(default_factory=list)
    retrieved_evidence: list[RetrievedEvidence] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    evidence_checks: list[str] = Field(default_factory=list)
    coverage_by_category: dict[str, float] = Field(default_factory=dict)
    risk_score: float = Field(default=0.0, ge=0.0)
    evidence_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    rollback_readiness: str = "unknown"
    coverage_downgrade_reason: Optional[str] = None


class PolicyConfig(BaseModel):
    """Configurable deterministic decision thresholds."""

    model_config = ConfigDict(extra="forbid")

    policy_version: str = "mvp-v1"
    caution_score_threshold: float = Field(default=35.0, ge=0.0)
    hold_score_threshold: float = Field(default=95.0, ge=0.0)
    go_min_coverage: float = Field(default=0.8, ge=0.0, le=1.0)
    hold_min_coverage: float = Field(default=0.5, ge=0.0, le=1.0)


class PolicyDecision(BaseModel):
    """Final recommendation from deterministic decision policy."""

    model_config = ConfigDict(extra="forbid")

    decision: DecisionLabel
    rationale: str = Field(min_length=1)
    triggered_conditions: list[str] = Field(default_factory=list)
    policy_version: str = Field(default="mvp-v1")
    downgraded_for_coverage: bool = False
    base_decision: Optional[DecisionLabel] = None


class RiskMemo(BaseModel):
    """Human-readable assessment summary produced by a provider."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1)
    executive_summary: Optional[str] = None
    decision_rationale: Optional[str] = None
    top_risks: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    rollback_notes: Optional[str] = None
    recommended_next_steps: list[str] = Field(default_factory=list)
    recommendation: DecisionLabel
    provider_name: str = Field(min_length=1)
    deterministic: bool = True


class Assessment(BaseModel):
    """Complete decision-support artifact for one release."""

    model_config = ConfigDict(extra="forbid")

    assessment_id: str = Field(min_length=1)
    evaluated_at: datetime
    bundle: ReleaseBundle
    rules: RulesEvaluation
    decision: PolicyDecision
    memo: RiskMemo
    retrieved_evidence: list[RetrievedEvidence] = Field(default_factory=list)


class AssessmentHistoryItem(BaseModel):
    """Lightweight assessment summary for history views."""

    model_config = ConfigDict(extra="forbid")

    assessment_id: str
    release_id: str
    service: str
    environment: str
    created_at: datetime
    evaluated_at: datetime
    decision: DecisionLabel
    risk_score: float
