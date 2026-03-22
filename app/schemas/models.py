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

    model_config = ConfigDict(extra="forbid")

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


class RulesEvaluation(BaseModel):
    """Aggregated output from the deterministic rules engine."""

    model_config = ConfigDict(extra="forbid")

    hard_blocks: list[RuleFinding] = Field(default_factory=list)
    risk_flags: list[RuleFinding] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    evidence_checks: list[str] = Field(default_factory=list)
    risk_score: float = Field(default=0.0, ge=0.0)
    evidence_coverage: float = Field(default=0.0, ge=0.0, le=1.0)


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


class RiskMemo(BaseModel):
    """Human-readable assessment summary produced by a provider."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1)
    top_risks: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
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
