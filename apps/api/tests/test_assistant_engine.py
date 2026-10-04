import pytest

from services.ai.assistant.engine import AssistantUpstreamError, run_chat_turn
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


class _Namespace:
    def __init__(self, **fields):
        self.__dict__.update(fields)


class _FakeFileDownload:
    def __init__(self, content: bytes):
        self._content = content

    def write_to_file(self, path):
        with open(path, "wb") as f:
            f.write(self._content)


def test_generated_pdf_is_downloaded_and_returned(monkeypatch):
    output = _Namespace(type="bash_code_execution_output", file_id="file_abc")
    exec_result = _Namespace(type="bash_code_execution_result", content=[output])
    code_block = _FakeBlock("bash_code_execution_tool_result", content=exec_result)
    text_block = _FakeBlock("text", text="Here's your PDF.")

    class _FakeFiles:
        def retrieve_metadata(self, file_id):
            assert file_id == "file_abc"
            return _Namespace(filename="report.pdf", mime_type="application/pdf")

        def download(self, file_id):
            assert file_id == "file_abc"
            return _FakeFileDownload(b"%PDF-1.4 fake pdf bytes")

    class _FakeMessages:
        def create(self, **kwargs):
            return _FakeResponse("end_turn", [code_block, text_block])

    class _FakeClient:
        def __init__(self, api_key):
            self.messages = _FakeMessages()
            self.files = _FakeFiles()

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", _FakeClient)

    result = run_chat_turn(
        "anthropic", "key", "claude-opus-5", [{"role": "user", "content": "make me a pdf"}],
        lambda n, i: {},
    )

    assert result.reply == "Here's your PDF."
    assert len(result.generated_files) == 1
    generated = result.generated_files[0]
    assert generated.filename == "report.pdf"
    assert generated.media_type == "application/pdf"
    assert generated.content == b"%PDF-1.4 fake pdf bytes"


def test_empty_text_blocks_are_stripped_before_the_call(monkeypatch):
    # Anthropic 400s the whole request on any empty text block; one can come
    # back in the model's own reply and then be resent as history.
    sent = {}

    class _FakeMessages:
        def create(self, **kwargs):
            sent["messages"] = list(kwargs["messages"])
            return _FakeResponse("end_turn", [_FakeBlock("text", text="Fine.")])

    class _FakeClient:
        def __init__(self, api_key):
            self.messages = _FakeMessages()

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", _FakeClient)

    history = [
        {"role": "user", "content": "first"},
        {
            "role": "assistant",
            "content": [{"type": "text", "text": ""}, {"type": "text", "text": "reply"}],
        },
        {"role": "assistant", "content": [{"type": "text", "text": "  "}]},
        {"role": "user", "content": ""},
        {"role": "user", "content": "second"},
    ]
    result = run_chat_turn("anthropic", "key", "claude-opus-5", history, lambda n, i: {})

    assert sent["messages"] == [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": [{"type": "text", "text": "reply"}]},
        {"role": "user", "content": "second"},
    ]
    assert result.reply == "Fine."


def test_orphaned_server_tool_use_is_stripped_on_max_tokens_truncation(monkeypatch):
    # code_execution's call and result normally land in the same turn, but
    # hitting max_tokens mid-call can cut the response off between the two.
    # Persisting that orphan as history gets the whole next request
    # rejected by Anthropic — it must be dropped before it's ever stored.
    class _FakeMessages:
        def create(self, **kwargs):
            return _FakeResponse(
                "max_tokens",
                [
                    _FakeBlock("text", text="Let me check that."),
                    _FakeBlock(
                        "server_tool_use", id="srvtoolu_01abc", name="code_execution", input={}
                    ),
                ],
            )

    class _FakeClient:
        def __init__(self, api_key):
            self.messages = _FakeMessages()

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", _FakeClient)

    result = run_chat_turn(
        "anthropic", "key", "claude-opus-5", [{"role": "user", "content": "hi"}], lambda n, i: {}
    )

    assistant_message = result.messages[-1]
    assert assistant_message["role"] == "assistant"
    assert [b["type"] for b in assistant_message["content"]] == ["text"]


def test_paired_server_tool_use_is_kept(monkeypatch):
    class _FakeMessages:
        def create(self, **kwargs):
            return _FakeResponse(
                "end_turn",
                [
                    _FakeBlock(
                        "server_tool_use", id="srvtoolu_01abc", name="code_execution", input={}
                    ),
                    _FakeBlock(
                        "bash_code_execution_tool_result",
                        tool_use_id="srvtoolu_01abc",
                        content={"type": "bash_code_execution_result"},
                    ),
                    _FakeBlock("text", text="Done."),
                ],
            )

    class _FakeClient:
        def __init__(self, api_key):
            self.messages = _FakeMessages()

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", _FakeClient)

    result = run_chat_turn(
        "anthropic", "key", "claude-opus-5", [{"role": "user", "content": "hi"}], lambda n, i: {}
    )

    assistant_message = result.messages[-1]
    types = [b["type"] for b in assistant_message["content"]]
    assert "server_tool_use" in types
    assert "bash_code_execution_tool_result" in types


def test_provider_error_becomes_assistant_upstream_error(monkeypatch):
    import anthropic
    import httpx2

    class _FakeMessages:
        def create(self, **kwargs):
            raise anthropic.APIConnectionError(request=httpx2.Request("POST", "https://x"))

    class _FakeClient:
        def __init__(self, api_key):
            self.messages = _FakeMessages()

    monkeypatch.setattr(anthropic, "Anthropic", _FakeClient)

    with pytest.raises(AssistantUpstreamError):
        run_chat_turn(
            "anthropic", "key", "claude-opus-5", [{"role": "user", "content": "hi"}], lambda n, i: {}
        )
