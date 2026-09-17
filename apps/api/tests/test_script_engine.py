import pytest

from services.ai.script.engine import (
    SceneDraft,
    ScriptEngine,
    _SceneModel,
    _SceneRegenerateModel,
    _ScriptDraftModel,
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
