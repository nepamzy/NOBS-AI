import json
import logging

from services.voice.chatterbox.adapter import ChatterboxEngine
from services.voice.elevenlabs.adapter import ElevenLabsEngine
from services.voice.engine import VoiceEngine

logger = logging.getLogger(__name__)


def _parse_voice_map(raw: str, env_name: str) -> dict[str, str]:
    """The voice map only renames presets to provider voice IDs. A malformed
    value used to crash every job at startup; fall back to defaults and say so."""
    try:
        parsed = json.loads(raw or "{}")
    except json.JSONDecodeError:
        logger.warning("%s is not valid JSON; using default voices instead", env_name)
        return {}
    return parsed if isinstance(parsed, dict) else {}


def get_voice_engine(
    voice_provider: str,
    chatterbox_api_url: str,
    elevenlabs_api_key: str,
    elevenlabs_voice_map_json: str,
    chatterbox_voice_map_json: str = "{}",
) -> VoiceEngine:
    if voice_provider == "elevenlabs":
        voice_map = _parse_voice_map(elevenlabs_voice_map_json, "ELEVENLABS_VOICE_MAP")
        return ElevenLabsEngine(api_key=elevenlabs_api_key, voice_map=voice_map)
    chatterbox_voice_map = _parse_voice_map(chatterbox_voice_map_json, "CHATTERBOX_VOICE_MAP")
    return ChatterboxEngine(chatterbox_api_url, voice_map=chatterbox_voice_map)
