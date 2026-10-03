import pytest

from services.clipping.transcription.engine import TranscriptResult, Word
from services.common.errors import ApprovalRequiredError, EngineNotConfiguredError
from services.voice.chatterbox.adapter import ChatterboxEngine
from services.voice.factory import get_voice_engine


class _FakeTranscriber:
    def transcribe(self, audio_path):
        return TranscriptResult(
            full_text="hi there",
            words=[
                Word(word="hi", start=0.0, end=0.2),
                Word(word="there", start=0.4, end=0.9),
            ],
        )


def test_raises_when_not_configured():
    engine = ChatterboxEngine(api_url="")
    with pytest.raises(ApprovalRequiredError):
        engine.synthesize("hello world", "warm-narrator", "/tmp/does-not-matter.wav")


def test_raises_when_preset_unmapped():
    engine = ChatterboxEngine(api_url="http://localhost:9000", voice_map={})
    with pytest.raises(EngineNotConfiguredError):
        engine.synthesize("hello world", "warm-narrator", "/tmp/does-not-matter.wav")


def test_synthesizes_real_call_measures_duration_and_transcribes_words(tmp_path, monkeypatch):
    calls = []

    class _FakeResponse:
        content = b"fake wav bytes"

        def raise_for_status(self):
            pass

    def fake_post(url, json=None, timeout=None):
        calls.append({"url": url, "json": json, "timeout": timeout})
        return _FakeResponse()

    import services.voice.chatterbox.adapter as adapter_module

    monkeypatch.setattr(adapter_module.httpx, "post", fake_post)
    monkeypatch.setattr(adapter_module, "probe_duration_seconds", lambda path: 0.9)

    output_path = str(tmp_path / "voiceover.wav")
    engine = ChatterboxEngine(
        api_url="http://localhost:9000", voice_map={"warm-narrator": "my_voice.wav"}
    )
    engine._transcriber = _FakeTranscriber()

    result = engine.synthesize("hi there", "warm-narrator", output_path)

    assert len(calls) == 1
    assert calls[0]["url"] == "http://localhost:9000/v1/audio/speech"
    assert calls[0]["json"] == {
        "model": "chatterbox",
        "input": "hi there",
        "voice": "my_voice.wav",
        "response_format": "wav",
    }

    assert result.audio_path == output_path
    with open(output_path, "rb") as f:
        assert f.read() == b"fake wav bytes"

    assert result.duration_seconds == 0.9
    assert [w["word"] for w in result.word_timestamps] == ["hi", "there"]
    assert result.word_timestamps[1] == {"word": "there", "start": 0.4, "end": 0.9}


def test_factory_builds_chatterbox_with_voice_map():
    engine = get_voice_engine(
        "chatterbox", "http://localhost:9000", "", "{}", '{"warm-narrator": "voice.wav"}'
    )
    assert isinstance(engine, ChatterboxEngine)
    assert engine._voice_map == {"warm-narrator": "voice.wav"}
