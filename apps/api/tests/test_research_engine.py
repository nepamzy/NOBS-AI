import json
from types import SimpleNamespace

import pytest

from services.ai.research.engine import ResearchEngine, ResearchOutputError
from services.common.errors import ApprovalRequiredError, EngineNotConfiguredError

_GOOD = {
    "key_facts": ["fact one"],
    "statistics": ["42%"],
    "interesting_findings": ["finding one"],
    "counterarguments": ["counter one"],
    "story_opportunities": ["angle one"],
    "sources": [{"url": "https://example.com", "title": "Example", "excerpt": "..."}],
}


def _reply(text, stop_reason="end_turn"):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], stop_reason=stop_reason)


def _install_fake_client(monkeypatch, replies):
    """Each call to messages.create pops the next reply from `replies`."""
    calls = []

    class _FakeMessages:
        def create(self, **kwargs):
            calls.append(kwargs)
            return replies.pop(0)

    class _FakeClient:
        def __init__(self, api_key):
            calls.append({"api_key": api_key})
            self.messages = _FakeMessages()

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", _FakeClient)
    return calls


def _engine():
    return ResearchEngine(llm_provider="anthropic", llm_api_key="key123", llm_model="claude-opus-5")


def test_raises_when_not_configured():
    engine = ResearchEngine(llm_provider="", llm_api_key="")
    with pytest.raises(ApprovalRequiredError):
        engine.run("how black holes form")


def test_raises_for_unimplemented_provider():
    engine = ResearchEngine(llm_provider="openai", llm_api_key="key")
    with pytest.raises(EngineNotConfiguredError):
        engine.run("how black holes form")


def test_run_calls_anthropic_and_maps_result(monkeypatch):
    calls = _install_fake_client(monkeypatch, [_reply(json.dumps(_GOOD))])

    result = _engine().run("how black holes form")

    assert calls[0] == {"api_key": "key123"}
    assert calls[1]["model"] == "claude-opus-5"

    assert result.topic == "how black holes form"
    assert result.key_facts == ["fact one"]
    assert result.sources == [{"url": "https://example.com", "title": "Example", "excerpt": "..."}]


def test_accepts_json_wrapped_in_prose_or_a_code_fence(monkeypatch):
    wrapped = "Here you go:\n```json\n" + json.dumps(_GOOD) + "\n```"
    _install_fake_client(monkeypatch, [_reply(wrapped)])

    assert _engine().run("topic").key_facts == ["fact one"]


def test_retries_once_when_first_reply_is_not_json(monkeypatch):
    calls = _install_fake_client(
        monkeypatch, [_reply("Sorry, I can't do that."), _reply(json.dumps(_GOOD))]
    )

    result = _engine().run("topic")

    assert result.key_facts == ["fact one"]
    assert len(calls) == 3  # api_key + two create() calls


def test_cut_off_reply_fails_with_a_clear_reason(monkeypatch):
    _install_fake_client(
        monkeypatch,
        [_reply('{"key_facts": ["', stop_reason="max_tokens")] * 2,
    )

    with pytest.raises(ResearchOutputError, match="cut off"):
        _engine().run("topic")


def test_garbage_twice_fails_with_the_start_of_the_reply(monkeypatch):
    _install_fake_client(monkeypatch, [_reply("nope")] * 2)

    with pytest.raises(ResearchOutputError, match="starts with: 'nope'"):
        _engine().run("topic")
