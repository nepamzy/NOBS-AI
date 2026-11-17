import pytest

from services.ai.script.engine import (
    SceneDraft,
    ScriptEngine,
    _SceneModel,
    _SceneRegenerateModel,
    _ScriptDraftModel,
    _ScriptPartModel,
)
from services.common.errors import ApprovalRequiredError, EngineNotConfiguredError


def test_generate_raises_when_not_configured():
    engine = ScriptEngine(llm_provider="", llm_api_key="")
    with pytest.raises(ApprovalRequiredError):
        engine.generate("how black holes form", 180)


def test_generate_raises_for_unimplemented_provider():
    engine = ScriptEngine(llm_provider="openai", llm_api_key="key")
    with pytest.raises(EngineNotConfiguredError):
        engine.generate("how black holes form", 180)


def test_generate_calls_anthropic_and_maps_scenes(monkeypatch):
    calls = []

    class _FakeResponse:
        parsed_output = _ScriptDraftModel(
            title="Black Holes Explained",
            hook="What if nothing could escape?",
            estimated_duration_seconds=180,
            word_count=450,
            scenes=[
                _SceneModel(
                    order=1,
                    narration="Black holes form when stars collapse.",
                    visual_prompt="A star collapsing into a black hole",
                    duration_seconds=8,
                    transition="cut",
                )
            ],
        )

    class _FakeMessages:
        def parse(self, **kwargs):
            calls.append(kwargs)
            return _FakeResponse()

    class _FakeClient:
        def __init__(self, api_key):
            self.messages = _FakeMessages()

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", _FakeClient)

    engine = ScriptEngine(llm_provider="anthropic", llm_api_key="key123")
    draft = engine.generate("how black holes form", 180)

    assert calls[0]["output_format"] is _ScriptDraftModel
    assert draft.title == "Black Holes Explained"
    assert len(draft.scenes) == 1
    assert draft.scenes[0].narration == "Black holes form when stars collapse."
    assert draft.scenes[0].transition == "cut"


def test_regenerate_scene_raises_when_not_configured():
    engine = ScriptEngine(llm_provider="", llm_api_key="")
    scene = SceneDraft(order=1, narration="old", visual_prompt="old prompt", duration_seconds=8)
    with pytest.raises(ApprovalRequiredError):
        engine.regenerate_scene("how black holes form", scene)


def test_regenerate_scene_calls_anthropic_and_keeps_order(monkeypatch):
    class _FakeResponse:
        parsed_output = _SceneRegenerateModel(
            narration="new narration", visual_prompt="new visual prompt"
        )

    class _FakeMessages:
        def parse(self, **kwargs):
            return _FakeResponse()

    class _FakeClient:
        def __init__(self, api_key):
            self.messages = _FakeMessages()

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", _FakeClient)

    engine = ScriptEngine(llm_provider="anthropic", llm_api_key="key123")
    scene = SceneDraft(
        order=3, narration="old", visual_prompt="old prompt", duration_seconds=8, transition="fade"
    )
    updated = engine.regenerate_scene(
        "how black holes form", scene, instructions="make it punchier"
    )

    assert updated.order == 3
    assert updated.duration_seconds == 8
    assert updated.transition == "fade"
    assert updated.narration == "new narration"
    assert updated.visual_prompt == "new visual prompt"


# ---- long scripts: reply size, parts, and clear failures -----------------------------


class _Resp:
    def __init__(self, parsed, stop_reason="end_turn"):
        self.parsed_output = parsed
        self.stop_reason = stop_reason


def _scene(i, seconds=8):
    return _SceneModel(
        order=i, narration=f"narration {i} " + "word " * 18,
        visual_prompt=f"visual {i}", duration_seconds=seconds, transition="cut",
    )


def _install_client(monkeypatch, handler):
    import anthropic

    calls = []

    class _Messages:
        def parse(self, **kwargs):
            calls.append(kwargs)
            return handler(kwargs, len(calls))

    class _Client:
        def __init__(self, api_key):
            self.messages = _Messages()

    monkeypatch.setattr(anthropic, "Anthropic", _Client)
    return calls


def _engine():
    return ScriptEngine(llm_provider="anthropic", llm_api_key="k")


def test_reply_size_grows_with_the_video_instead_of_a_fixed_4096(monkeypatch):
    calls = _install_client(
        monkeypatch,
        lambda kw, n: _Resp(_ScriptDraftModel(title="T", hook="H", estimated_duration_seconds=1,
                                              word_count=1, scenes=[_scene(1)])),
    )
    _engine().generate("topic", 20)
    _engine().generate("topic", 180)
    assert calls[0]["max_tokens"] == 4096  # tiny video: the floor
    assert calls[1]["max_tokens"] > 4096  # 3 minutes is ~23 scenes: needs more than the old cap
    assert all(c["max_tokens"] <= 16000 for c in calls)


def test_a_fifteen_minute_script_is_written_in_two_parts_and_stitched(monkeypatch):
    def handler(kw, n):
        if n == 1:
            return _Resp(_ScriptDraftModel(
                title="The Big One", hook="Listen.", estimated_duration_seconds=1, word_count=1,
                scenes=[_scene(i) for i in range(1, 51)]))
        return _Resp(_ScriptPartModel(scenes=[_scene(i) for i in range(1, 61)]))

    calls = _install_client(monkeypatch, handler)
    draft = _engine().generate("a story", 900)

    assert len(calls) == 2
    assert calls[0]["output_format"] is _ScriptDraftModel
    assert calls[1]["output_format"] is _ScriptPartModel
    assert all(c["max_tokens"] <= 16000 for c in calls)

    first, second = calls[0]["messages"][0]["content"], calls[1]["messages"][0]["content"]
    assert "part 1 of 2" in first and "do NOT wrap the story up" in first
    assert "part 2 of 2" in second and "The Big One" in second  # knows the title
    assert "narration 50" in second  # and where part 1 ended
    assert "FINAL part" in second

    assert draft.title == "The Big One" and len(draft.scenes) == 110
    assert [s.order for s in draft.scenes] == list(range(1, 111))  # one continuous numbering
    assert draft.estimated_duration_seconds == 110 * 8  # measured from the scenes
    assert draft.word_count == sum(len(s.narration.split()) for s in draft.scenes)


def test_a_cut_off_reply_says_so_instead_of_crashing_on_none(monkeypatch):
    from services.ai.parsing import ModelOutputError

    _install_client(monkeypatch, lambda kw, n: _Resp(None, stop_reason="max_tokens"))
    with pytest.raises(ModelOutputError) as caught:
        _engine().generate("topic", 180)
    assert "cut off" in str(caught.value) and "NoneType" not in str(caught.value)


def test_a_refusal_and_an_unreadable_reply_are_explained(monkeypatch):
    from services.ai.parsing import ModelOutputError

    _install_client(monkeypatch, lambda kw, n: _Resp(None, stop_reason="refusal"))
    with pytest.raises(ModelOutputError, match="declined"):
        _engine().generate("topic", 60)

    _install_client(monkeypatch, lambda kw, n: _Resp(None, stop_reason="end_turn"))
    with pytest.raises(ModelOutputError, match="end_turn"):
        _engine().generate("topic", 60)


def test_a_failure_in_a_later_part_is_attributed_to_that_part(monkeypatch):
    from services.ai.parsing import ModelOutputError

    def handler(kw, n):
        if n == 1:
            return _Resp(_ScriptDraftModel(title="T", hook="H", estimated_duration_seconds=1,
                                           word_count=1, scenes=[_scene(1)]))
        return _Resp(None, stop_reason="max_tokens")

    _install_client(monkeypatch, handler)
    with pytest.raises(ModelOutputError, match="part 2"):
        _engine().generate("topic", 900)


def test_an_absurdly_long_video_is_refused_before_any_ai_call(monkeypatch):
    from services.ai.script.engine import ScriptLengthError

    calls = _install_client(monkeypatch, lambda kw, n: _Resp(None))
    with pytest.raises(ScriptLengthError, match="48 minutes"):
        _engine().generate("topic", 4 * 3600)
    assert calls == []  # nothing was sent, so nothing was billed


def test_regenerate_scene_reports_an_unreadable_reply(monkeypatch):
    from services.ai.parsing import ModelOutputError

    _install_client(monkeypatch, lambda kw, n: _Resp(None, stop_reason="max_tokens"))
    scene = SceneDraft(order=1, narration="n", visual_prompt="v", duration_seconds=8)
    with pytest.raises(ModelOutputError):
        _engine().regenerate_scene("topic", scene)
