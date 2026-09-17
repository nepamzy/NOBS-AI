import json

from services.voice.chatterbox.adapter import ChatterboxEngine
from services.voice.elevenlabs.adapter import ElevenLabsEngine
from services.voice.engine import VoiceEngine


def get_voice_engine(
    voice_provider: str,
    chatterbox_api_url: str,
    elevenlabs_api_key: str,
    elevenlabs_voice_map_json: str,
) -> VoiceEngine:
    if voice_provider == "elevenlabs":
        voice_map: dict[str, str] = json.loads(elevenlabs_voice_map_json or "{}")
        return ElevenLabsEngine(api_key=elevenlabs_api_key, voice_map=voice_map)
    return ChatterboxEngine(chatterbox_api_url)
