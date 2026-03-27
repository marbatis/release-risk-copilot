"""Deterministic local evidence retrieval for release assessment."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.models import (
    DependencySignal,
    EvidenceSourceType,
    IncidentSignal,
    ReleaseBundle,
    RetrievedEvidence,
    ServiceOwnership,
)

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DEPENDENCY_DATA = DATA_DIR / "dependencies" / "dependencies.json"
INCIDENT_DATA = DATA_DIR / "incidents" / "incidents.json"
OWNERSHIP_DATA = DATA_DIR / "ownership" / "ownership.json"
RUNBOOK_DIR = DATA_DIR / "runbooks"
POLICY_FILE = DATA_DIR / "policies" / "risk_policy.yaml"


class RetrievalResult(BaseModel):
    """Result of deterministic retrieval for one bundle."""

    model_config = ConfigDict(extra="forbid")

    normalized_bundle: ReleaseBundle
    evidence: list[RetrievedEvidence]


class RetrievalService:
    """Load deterministic local corpora and attach relevant evidence."""

    def __init__(
        self,
        dependency_data: Path = DEPENDENCY_DATA,
        incident_data: Path = INCIDENT_DATA,
        ownership_data: Path = OWNERSHIP_DATA,
        runbook_dir: Path = RUNBOOK_DIR,
        policy_file: Path = POLICY_FILE,
    ) -> None:
        self.dependency_data = dependency_data
        self.incident_data = incident_data
        self.ownership_data = ownership_data
        self.runbook_dir = runbook_dir
        self.policy_file = policy_file

    def retrieve(self, bundle: ReleaseBundle) -> RetrievalResult:
        """Return bundle augmented with local deterministic evidence."""

        normalized_bundle = bundle.model_copy(deep=True)
        evidence: list[RetrievedEvidence] = []

        retrieved_dependencies = self._retrieve_dependencies(bundle)
        retrieved_incidents = self._retrieve_incidents(bundle)
        retrieved_ownership = self._retrieve_ownership(bundle)
        retrieved_runbook = self._retrieve_runbook(bundle)
        retrieved_policy = self._retrieve_policy()

        dependency_signals = [item for item, _ in retrieved_dependencies]
        incident_signals = [item for item, _ in retrieved_incidents]

        evidence.extend(item for _, item in retrieved_dependencies)
        evidence.extend(item for _, item in retrieved_incidents)
        evidence.extend(item for _, item in retrieved_ownership)
        evidence.extend(item for _, item in retrieved_runbook)
        evidence.extend(item for _, item in retrieved_policy)

        if dependency_signals:
            normalized_bundle.dependencies = self._merge_dependencies(bundle.dependencies, dependency_signals)

        if incident_signals:
            normalized_bundle.recent_incidents = self._merge_incidents(bundle.recent_incidents, incident_signals)

        if bundle.ownership is None and retrieved_ownership:
            normalized_bundle.ownership = retrieved_ownership[0][0]

        if bundle.runbook_link_present is None and retrieved_runbook:
            normalized_bundle.runbook_link_present = True

        return RetrievalResult(normalized_bundle=normalized_bundle, evidence=evidence)

    def _retrieve_dependencies(self, bundle: ReleaseBundle) -> list[tuple[DependencySignal, RetrievedEvidence]]:
        records = self._load_json_list(self.dependency_data)
        results: list[tuple[DependencySignal, RetrievedEvidence]] = []

        for record in records:
            if record.get("service") != bundle.service:
                continue
            if record.get("environment") != bundle.environment:
                continue

            signal = DependencySignal.model_validate(record["signal"])
            evidence = RetrievedEvidence(
                source_type=EvidenceSourceType.DEPENDENCY,
                source_name=signal.name,
                excerpt=f"Dependency {signal.name} is {signal.status.value}.",
                relevance_score=0.9 if signal.status.value in {"down", "degraded"} else 0.7,
                source_ref=f"dependencies/{self.dependency_data.name}",
            )
            results.append((signal, evidence))

        return results

    def _retrieve_incidents(self, bundle: ReleaseBundle) -> list[tuple[IncidentSignal, RetrievedEvidence]]:
        records = self._load_json_list(self.incident_data)
        results: list[tuple[IncidentSignal, RetrievedEvidence]] = []

        for record in records:
            if record.get("linked_service") != bundle.service:
                continue

            signal = IncidentSignal.model_validate(record)
            relevance = 0.95 if signal.severity.value in {"SEV1", "SEV2"} else 0.65
            evidence = RetrievedEvidence(
                source_type=EvidenceSourceType.INCIDENT,
                source_name=signal.incident_id,
                excerpt=(
                    f"Incident {signal.incident_id} ({signal.severity.value}) "
                    f"status={signal.status.value} for {signal.linked_service}."
                ),
                relevance_score=relevance,
                source_ref=f"incidents/{self.incident_data.name}",
            )
            results.append((signal, evidence))

        return results

    def _retrieve_ownership(self, bundle: ReleaseBundle) -> list[tuple[ServiceOwnership, RetrievedEvidence]]:
        records = self._load_json_list(self.ownership_data)
        results: list[tuple[ServiceOwnership, RetrievedEvidence]] = []

        for record in records:
            if record.get("service") != bundle.service:
                continue

            ownership = ServiceOwnership.model_validate(record)
            evidence = RetrievedEvidence(
                source_type=EvidenceSourceType.OWNERSHIP,
                source_name=ownership.service,
                excerpt=f"Owning team: {ownership.owning_team}, oncall_defined={ownership.oncall_defined}",
                relevance_score=0.8,
                source_ref=f"ownership/{self.ownership_data.name}",
            )
            results.append((ownership, evidence))

        return results

    def _retrieve_runbook(self, bundle: ReleaseBundle) -> list[tuple[dict[str, Any], RetrievedEvidence]]:
        service_name = bundle.service.replace("/", "-")
        runbook_path = self.runbook_dir / f"{service_name}.md"
        if not runbook_path.exists():
            return []

        content = runbook_path.read_text(encoding="utf-8").strip()
        excerpt = content.splitlines()[0] if content else "Runbook file available"
        evidence = RetrievedEvidence(
            source_type=EvidenceSourceType.RUNBOOK,
            source_name=runbook_path.name,
            excerpt=excerpt,
            relevance_score=0.75,
            source_ref=f"runbooks/{runbook_path.name}",
        )
        return [({}, evidence)]

    def _retrieve_policy(self) -> list[tuple[dict[str, Any], RetrievedEvidence]]:
        if not self.policy_file.exists():
            return []

        text = self.policy_file.read_text(encoding="utf-8").strip()
        if not text:
            return []

        excerpt = text.splitlines()[0]
        evidence = RetrievedEvidence(
            source_type=EvidenceSourceType.POLICY,
            source_name=self.policy_file.name,
            excerpt=excerpt,
            relevance_score=0.55,
            source_ref=f"policies/{self.policy_file.name}",
        )
        return [({}, evidence)]

    @staticmethod
    def _merge_dependencies(
        existing: Optional[list[DependencySignal]],
        retrieved: list[DependencySignal],
    ) -> list[DependencySignal]:
        if not existing:
            return retrieved

        merged = {item.name: item for item in existing}
        for item in retrieved:
            merged.setdefault(item.name, item)
        return list(merged.values())

    @staticmethod
    def _merge_incidents(
        existing: Optional[list[IncidentSignal]],
        retrieved: list[IncidentSignal],
    ) -> list[IncidentSignal]:
        if not existing:
            return retrieved

        merged = {item.incident_id: item for item in existing}
        for item in retrieved:
            merged.setdefault(item.incident_id, item)
        return list(merged.values())

    @staticmethod
    def _load_json_list(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []

        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            return []
        return [item for item in payload if isinstance(item, dict)]
