"""OpenAI provider schema fallback behavior tests."""

from app.providers.openai_provider import OpenAIMemoProvider
from app.services.decision_policy import DecisionPolicy
from app.services.risk_scoring import RiskScoringService
from app.services.rules_engine import RulesEngine
from app.services.sample_data import SampleDataRepository


class _FakeResponse:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text


class _FakeResponsesClient:
    def __init__(self, output_text: str) -> None:
        self._output_text = output_text

    def create(self, **_: object) -> _FakeResponse:
        return _FakeResponse(self._output_text)


class _FakeOpenAIClient:
    def __init__(self, output_text: str) -> None:
        self.responses = _FakeResponsesClient(output_text)


def _build_inputs():
    repo = SampleDataRepository()
    bundle = repo.load_sample("go_clean_release")
    rules = RulesEngine().evaluate(bundle)
    rules = rules.model_copy(update={"risk_score": RiskScoringService().score(rules)})
    decision = DecisionPolicy().decide(rules)
    return bundle, rules, decision


def test_openai_provider_falls_back_to_mock_on_invalid_json() -> None:
    provider = OpenAIMemoProvider(
        api_key="test-key",
        model="gpt-5-mini",
        client=_FakeOpenAIClient(output_text="not-json"),
    )
    bundle, rules, decision = _build_inputs()

    memo = provider.generate_memo(bundle, rules, decision)

    assert memo.provider_name == "mock"
    assert memo.deterministic is True


def test_openai_provider_uses_model_output_when_schema_is_valid() -> None:
    valid_json = (
        '{"executive_summary":"Safe with routine checks.",'
        '"decision_rationale":"Deterministic policy returned GO with adequate evidence.",'
        '"top_risks":["Minor deployment drift"],'
        '"missing_information":[],"rollback_notes":"Rollback ready.",'
        '"recommended_next_steps":["Proceed with canary verification"]}'
    )
    provider = OpenAIMemoProvider(
        api_key="test-key",
        model="gpt-5-mini",
        client=_FakeOpenAIClient(output_text=valid_json),
    )
    bundle, rules, decision = _build_inputs()

    memo = provider.generate_memo(bundle, rules, decision)

    assert memo.provider_name == "openai"
    assert memo.deterministic is False
    assert memo.recommendation.value == decision.decision.value
