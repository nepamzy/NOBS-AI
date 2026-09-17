"""ElevenLabs adapter — a managed, usage-based alternative to self-hosted
Chatterbox (see services/voice/chatterbox). Billed per character sent, with
no idle cost between calls — unlike self-hosting Chatterbox, which needs an
already-running server and bills for that server's uptime regardless of
whether it's synthesizing anything.

Uses the /with-timestamps endpoint so word-level timestamps (needed by
services/rendering/ffmpeg/captions.py) come back in the same call, instead
of a separate speech-recognition pass over the audio.
"""

import base64

import httpx

from services.common.errors import ApprovalRequiredError, CostWarning, EngineNotConfiguredError
from services.voice.engine import VoiceEngine, VoiceoverResult

_API_BASE_URL = "https://api.elevenlabs.io/v1"
_REQUEST_TIMEOUT_SECONDS = 60


def _characters_to_words(
    characters: list[str], starts: list[float], ends: list[float]
) -> list[dict]:
    """Groups ElevenLabs' per-character alignment into per-word timestamps
    (word starts at its first non-space character, ends at its last)."""
    words: list[dict] = []
    current = ""
    word_start: float | None = None
    word_end: float | None = None

    def flush() -> None:
        if current:
            words.append({"word": current, "start": word_start, "end": word_end})

    for char, start, end in zip(characters, starts, ends, strict=True):
        if char.isspace():
            flush()
            current = ""
            word_start = None
            continue
        if word_start is None:
            word_start = start
        current += char
        word_end = end
    flush()
    return words


class ElevenLabsEngine(VoiceEngine):
    def __init__(self, api_key: str, voice_map: dict[str, str]):
        self._api_key = api_key
        self._voice_map = voice_map

    def synthesize(self, text: str, voice_preset: str, output_path: str) -> VoiceoverResult:
        if not self._api_key:
            raise ApprovalRequiredError(
                CostWarning(
                    action=f"Synthesize {len(text)}-character voiceover via ElevenLabs",
                    service="ElevenLabs Text-to-Speech API",
                    expected_cost="~$0.10 per 1,000 characters (multilingual "
                    "model) — re-verify current pricing before relying on "
                    "this figure",
                    billing_type="usage-based (per character sent)",
                    max_expected_cost=f"~${len(text) / 1000 * 0.10:.4f} for "
                    "this call at $0.10/1,000 chars",
                    risk="Low",
                    why_needed="No ELEVENLABS_API_KEY configured.",
                )
            )
        voice_id = self._voice_map.get(voice_preset)
        if not voice_id:
            raise EngineNotConfiguredError(
                f"No ElevenLabs voice_id mapped for preset '{voice_preset}' — "
                "set it in ELEVENLABS_VOICE_MAP."
            )

        response = httpx.post(
            f"{_API_BASE_URL}/text-to-speech/{voice_id}/with-timestamps",
            headers={
                "xi-api-key": self._api_key,
                "Content-Type": "application/json",
            },
            json={"text": text, "model_id": "eleven_multilingual_v2"},
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()

        audio_bytes = base64.b64decode(payload["audio_base64"])
        with open(output_path, "wb") as f:
            f.write(audio_bytes)

        alignment = payload["alignment"]
        word_timestamps = _characters_to_words(
            alignment["characters"],
            alignment["character_start_times_seconds"],
            alignment["character_end_times_seconds"],
        )
        duration_seconds = alignment["character_end_times_seconds"][-1] if word_timestamps else 0.0

        return VoiceoverResult(
            audio_path=output_path,
            duration_seconds=duration_seconds,
            word_timestamps=word_timestamps,
        )
