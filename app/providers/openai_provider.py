"""OpenAI-backed memo provider with strict deterministic fallback."""

from __future__ import annotations

import json
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.providers.base import MemoProvider
from app.providers.mock_provider import MockMemoProvider
from app.schemas.models import PolicyDecision, ReleaseBundle, RiskMemo, RulesEvaluation

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - dependency/runtime guard
    OpenAI = None  # type: ignore[assignment]


class _MemoPayload(BaseModel):
    """Expected JSON payload shape from OpenAI Responses."""

    model_config = ConfigDict(extra="forbid")

    executive_summary: str
    decision_rationale: str
    top_risks: list[str]
    missing_information: list[str]
    rollback_notes: str
    recommended_next_steps: list[str]


class OpenAIMemoProvider(MemoProvider):
    """Generate explanatory memo via OpenAI; never decides final outcome."""

    name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str,
        client: Optional[Any] = None,
    ) -> None:
        self.model = model
        self._fallback = MockMemoProvider()
        self._disabled = False
        if client is not None:
            self.client = client
        elif OpenAI is not None:
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = None

    def generate_memo(
        self,
        bundle: ReleaseBundle,
        evaluation: RulesEvaluation,
        decision: PolicyDecision,
    ) -> RiskMemo:
        """Call OpenAI Responses API; fallback if output is invalid."""

        if self.client is None or self._disabled:
            return self._fallback.generate_memo(bundle, evaluation, decision)

        try:
            model_input = self._build_model_input(bundle, evaluation, decision)
            response = self.client.responses.create(
                model=self.model,
                input=[
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "input_text",
                                "text": (
                                    "You produce concise release risk memos. "
                                    "Use only provided deterministic evidence. "
                                    "Never change or challenge the final decision label."
                                ),
                            }
                        ],
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": (
                                    "Return JSON only with keys: executive_summary, "
                                    "decision_rationale, top_risks, missing_information, "
                                    "rollback_notes, recommended_next_steps.\n"
                                    f"Deterministic assessment input:\n{json.dumps(model_input, indent=2)}"
                                ),
                            }
                        ],
                    },
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "release_risk_memo",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "executive_summary": {"type": "string"},
                                "decision_rationale": {"type": "string"},
                                "top_risks": {"type": "array", "items": {"type": "string"}},
                                "missing_information": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "rollback_notes": {"type": "string"},
                                "recommended_next_steps": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "required": [
                                "executive_summary",
                                "decision_rationale",
                                "top_risks",
                                "missing_information",
                                "rollback_notes",
                                "recommended_next_steps",
                            ],
                        },
                    }
                },
            )
            payload = _MemoPayload.model_validate_json(self._extract_output_text(response))
            return RiskMemo(
                summary=payload.executive_summary,
                executive_summary=payload.executive_summary,
                decision_rationale=payload.decision_rationale,
                top_risks=payload.top_risks,
                missing_evidence=evaluation.missing_evidence,
                missing_information=payload.missing_information,
                supporting_evidence=[
                    item.source_ref or item.source_name for item in evaluation.retrieved_evidence[:5]
                ],
                rollback_notes=payload.rollback_notes,
                recommended_next_steps=payload.recommended_next_steps,
                recommendation=decision.decision,
                provider_name=self.name,
                deterministic=False,
            )
        except Exception:
            self._disabled = True
            return self._fallback.generate_memo(bundle, evaluation, decision)

    @staticmethod
    def _build_model_input(
        bundle: ReleaseBundle,
        evaluation: RulesEvaluation,
        decision: PolicyDecision,
    ) -> dict[str, Any]:
        """Create normalized deterministic input payload for model explanation."""

        return {
            "release_id": bundle.release_id,
            "service": bundle.service,
            "environment": bundle.environment,
            "decision": decision.decision.value,
            "policy_rationale": decision.rationale,
            "risk_score": evaluation.risk_score,
            "hard_blocks": [item.message for item in evaluation.hard_blocks],
            "rule_checks": [
                {
                    "rule_name": check.rule_name,
                    "passed": check.passed,
                    "severity": check.severity.value,
                    "message": check.message,
                }
                for check in evaluation.rule_checks
            ],
            "missing_evidence": evaluation.missing_evidence,
            "rollback_readiness": evaluation.rollback_readiness,
            "retrieved_evidence": [
                {
                    "source_type": evidence.source_type.value,
                    "source_name": evidence.source_name,
                    "excerpt": evidence.excerpt,
                    "relevance_score": evidence.relevance_score,
                    "source_ref": evidence.source_ref,
                }
                for evidence in evaluation.retrieved_evidence
            ],
        }

    @staticmethod
    def _extract_output_text(response: Any) -> str:
        """Extract text output robustly from Responses API result."""

        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                text = getattr(content, "text", None)
                if isinstance(text, str) and text.strip():
                    return text

        raise ValueError("No usable output text in response")
