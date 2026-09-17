import pytest

from services.ai.assistant.engine import run_chat_turn
from services.common.errors import ApprovalRequiredError, CostWarning, EngineNotConfiguredError


class _FakeBlock:
    def __init__(self, type_, **fields):
        self.type = type_
        self._fields = fields
        for key, value in fields.items():
            setattr(self, key, value)

    def model_dump(self):
        return {"type": self.type, **self._fields}


class _FakeResponse:
    def __init__(self, stop_reason, content):
        self.stop_reason = stop_reason
        self.content = content


def test_raises_when_not_configured():
    with pytest.raises(EngineNotConfiguredError):
        run_chat_turn("", "", "claude-opus-5", [], lambda name, inp: {})


def test_raises_for_unimplemented_provider():
    with pytest.raises(EngineNotConfiguredError):
        run_chat_turn("openai", "key", "claude-opus-5", [], lambda name, inp: {})


def test_plain_turn_with_no_tool_use(monkeypatch):
    class _FakeMessages:
        def create(self, **kwargs):
            return _FakeResponse("end_turn", [_FakeBlock("text", text="Hello!")])

    class _FakeClient:
        def __init__(self, api_key):
            self.messages = _FakeMessages()

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", _FakeClient)

    result = run_chat_turn(
        "anthropic", "key", "claude-opus-5", [{"role": "user", "content": "hi"}], lambda n, i: {}
    )
    assert result.reply == "Hello!"
    assert result.messages[-1]["role"] == "assistant"


def test_executes_tool_then_returns_final_reply(monkeypatch):
    calls = []
    responses = [
        _FakeResponse(
            "tool_use",
            [_FakeBlock("tool_use", id="tool1", name="list_projects", input={})],
        ),
        _FakeResponse("end_turn", [_FakeBlock("text", text="You have 1 project.")]),
    ]

    class _FakeMessages:
        def create(self, **kwargs):
            calls.append(kwargs)
            return responses.pop(0)

    class _FakeClient:
        def __init__(self, api_key):
            self.messages = _FakeMessages()

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", _FakeClient)

    def tool_executor(name, tool_input):
        assert name == "list_projects"
        return [{"id": "p1", "name": "My Project"}]

    result = run_chat_turn(
        "anthropic",
        "key",
        "claude-opus-5",
        [{"role": "user", "content": "list my projects"}],
        tool_executor,
    )

    assert result.reply == "You have 1 project."
    assert len(calls) == 2
    tool_result_message = result.messages[-2]
    assert tool_result_message["role"] == "user"
    assert tool_result_message["content"][0]["tool_use_id"] == "tool1"
    assert "My Project" in tool_result_message["content"][0]["content"]


def test_tool_approval_required_becomes_tool_error(monkeypatch):
    responses = [
        _FakeResponse(
            "tool_use",
            [_FakeBlock("tool_use", id="tool1", name="create_video", input={})],
        ),
        _FakeResponse("end_turn", [_FakeBlock("text", text="You're out of tokens.")]),
    ]

    class _FakeMessages:
        def create(self, **kwargs):
            return responses.pop(0)

    class _FakeClient:
        def __init__(self, api_key):
            self.messages = _FakeMessages()

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", _FakeClient)

    def tool_executor(name, tool_input):
        raise ApprovalRequiredError(
            CostWarning(
                action="a",
                service="b",
                expected_cost="c",
                billing_type="d",
                max_expected_cost="e",
                risk="f",
                why_needed="g",
            )
        )

    result = run_chat_turn(
        "anthropic", "key", "claude-opus-5", [{"role": "user", "content": "make a video"}],
        tool_executor,
    )
    assert result.reply == "You're out of tokens."
