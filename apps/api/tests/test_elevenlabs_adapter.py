import base64

import pytest

from services.common.errors import ApprovalRequiredError, EngineNotConfiguredError
from services.voice.elevenlabs.adapter import ElevenLabsEngine
from services.voice.factory import get_voice_engine


def test_raises_when_not_configured():
    engine = ElevenLabsEngine(api_key="", voice_map={})
    with pytest.raises(ApprovalRequiredError):
        engine.synthesize("hello world", "warm-narrator", "/tmp/does-not-matter.mp3")


def test_raises_when_preset_unmapped():
    engine = ElevenLabsEngine(api_key="key", voice_map={})
    with pytest.raises(EngineNotConfiguredError):
        engine.synthesize("hello world", "warm-narrator", "/tmp/does-not-matter.mp3")


def test_synthesizes_and_groups_characters_into_words(tmp_path, monkeypatch):
    calls = []

    class _FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "audio_base64": base64.b64encode(b"fake mp3 bytes").decode(),
                "alignment": {
                    "characters": list("hi there"),
                    "character_start_times_seconds": [0.0, 0.1, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
                    "character_end_times_seconds": [0.1, 0.2, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
                },
            }

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return _FakeResponse()

    import services.voice.elevenlabs.adapter as adapter_module

    monkeypatch.setattr(adapter_module.httpx, "post", fake_post)

    output_path = str(tmp_path / "voiceover.mp3")
    engine = ElevenLabsEngine(api_key="key", voice_map={"warm-narrator": "voice123"})
    result = engine.synthesize("hi there", "warm-narrator", output_path)

    assert len(calls) == 1
    assert calls[0]["url"] == "https://api.elevenlabs.io/v1/text-to-speech/voice123/with-timestamps"
    assert calls[0]["headers"]["xi-api-key"] == "key"
    assert calls[0]["json"] == {"text": "hi there", "model_id": "eleven_multilingual_v2"}

    assert result.audio_path == output_path
    with open(output_path, "rb") as f:
        assert f.read() == b"fake mp3 bytes"

    assert [w["word"] for w in result.word_timestamps] == ["hi", "there"]
    assert result.word_timestamps[0] == {"word": "hi", "start": 0.0, "end": 0.2}
    assert result.word_timestamps[1] == {"word": "there", "start": 0.4, "end": 0.9}
    assert result.duration_seconds == 0.9


def test_factory_selects_elevenlabs_when_configured():
    engine = get_voice_engine("elevenlabs", "", "key", '{"warm-narrator": "voice123"}')
    assert isinstance(engine, ElevenLabsEngine)


def test_factory_defaults_to_chatterbox():
    from services.voice.chatterbox.adapter import ChatterboxEngine

    engine = get_voice_engine("chatterbox", "http://localhost:9000", "", "{}")
    assert isinstance(engine, ChatterboxEngine)
