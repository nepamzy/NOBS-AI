import pytest

from services.ai.research.engine import ResearchEngine, _ResearchResultModel, _ResearchSourceModel
from services.common.errors import ApprovalRequiredError, EngineNotConfiguredError


def test_raises_when_not_configured():
    engine = ResearchEngine(llm_provider="", llm_api_key="")
    with pytest.raises(ApprovalRequiredError):
        engine.run("how black holes form")


def test_raises_for_unimplemented_provider():
    engine = ResearchEngine(llm_provider="openai", llm_api_key="key")
    with pytest.raises(EngineNotConfiguredError):
        engine.run("how black holes form")


def test_run_calls_anthropic_and_maps_result(monkeypatch):
    calls = []

    class _FakeResponse:
        parsed_output = _ResearchResultModel(
            key_facts=["fact one"],
            statistics=["42%"],
            interesting_findings=["finding one"],
            counterarguments=["counter one"],
            story_opportunities=["angle one"],
            sources=[
                _ResearchSourceModel(url="https://example.com", title="Example", excerpt="...")
            ],
        )

    class _FakeMessages:
        def parse(self, **kwargs):
            calls.append(kwargs)
            return _FakeResponse()

    class _FakeClient:
        def __init__(self, api_key):
            calls.append({"api_key": api_key})
            self.messages = _FakeMessages()

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", _FakeClient)

    engine = ResearchEngine(
        llm_provider="anthropic", llm_api_key="key123", llm_model="claude-opus-5"
    )
    result = engine.run("how black holes form")

    assert calls[0] == {"api_key": "key123"}
    assert calls[1]["model"] == "claude-opus-5"
    assert calls[1]["output_format"] is _ResearchResultModel

    assert result.topic == "how black holes form"
    assert result.key_facts == ["fact one"]
    assert result.sources == [{"url": "https://example.com", "title": "Example", "excerpt": "..."}]
