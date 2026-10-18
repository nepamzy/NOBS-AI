from services.voice.chatterbox.adapter import ChatterboxEngine
from services.voice.factory import get_voice_engine


def test_malformed_chatterbox_voice_map_falls_back_to_defaults():
    engine = get_voice_engine("chatterbox", "http://x", "", "{}", "not json at all")
    assert isinstance(engine, ChatterboxEngine)


def test_valid_chatterbox_voice_map_is_used():
    engine = get_voice_engine("chatterbox", "http://x", "", "{}", '{"narrator": "voice1"}')
    assert isinstance(engine, ChatterboxEngine)
