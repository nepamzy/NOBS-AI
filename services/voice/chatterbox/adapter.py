"""Chatterbox adapter (MIT license, self-hosted, OpenAI-compatible API at
POST /v1/audio/speech — see devnen/Chatterbox-TTS-Server on GitHub).
Self-hosting Chatterbox itself is free, but running it means a server
(local GPU/CPU or a rented one) must already exist, and starting *paid*
compute for it is gated by CLAUDE.md Part 1 just like Wan.

Chatterbox's own endpoint has no word-level timestamp output the way
ElevenLabs' /with-timestamps does — it only returns raw audio bytes. Real
word timestamps are measured here the honest way this app always prefers:
by running the SAME free local faster-whisper engine the clipping feature
already uses (services/clipping/transcription) over Chatterbox's own
generated audio, instead of estimating or faking them.
"""

from pathlib import Path

import httpx

from services.clipping.transcription.local_whisper.adapter import LocalWhisperEngine
from services.common.errors import ApprovalRequiredError, CostWarning, EngineNotConfiguredError
from services.common.media import probe_duration_seconds
from services.voice.engine import VoiceEngine, VoiceoverResult

_REQUEST_TIMEOUT_SECONDS = 120


class ChatterboxEngine(VoiceEngine):
    def __init__(self, api_url: str, voice_map: dict[str, str] | None = None):
        self._api_url = api_url.rstrip("/") if api_url else api_url
        self._voice_map = voice_map or {}
        # Free local compute, same engine/model the clipping feature uses —
        # not an approval-gated call, same reasoning as faster-whisper's own
        # adapter docstring.
        self._transcriber = LocalWhisperEngine()

    def synthesize(self, text: str, voice_preset: str, output_path: str) -> VoiceoverResult:
        if not self._api_url:
            raise ApprovalRequiredError(
                CostWarning(
                    action="Synthesize voiceover via Chatterbox",
                    service="Chatterbox (self-hosted)",
                    expected_cost="Free if self-hosted on already-running "
                    "hardware; COST UNKNOWN if it requires renting a GPU",
                    billing_type="unknown",
                    max_expected_cost="Unknown until a Chatterbox server is running",
                    risk="Unknown",
                    why_needed="No CHATTERBOX_API_URL is configured — a "
                    "Chatterbox server must be started (locally or rented) "
                    "and approved before voice synthesis can run.",
                )
            )
        voice_file = self._voice_map.get(voice_preset)
        if not voice_file:
            raise EngineNotConfiguredError(
                f"No Chatterbox voice file mapped for preset {voice_preset!r} — "
                "set it in CHATTERBOX_VOICE_MAP (maps a voice_preset id to a "
                "predefined or reference voice filename on the Chatterbox server)."
            )

        response = httpx.post(
            f"{self._api_url}/v1/audio/speech",
            json={
                "model": "chatterbox",
                "input": text,
                "voice": voice_file,
                "response_format": "wav",
            },
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        Path(output_path).write_bytes(response.content)

        duration_seconds = probe_duration_seconds(output_path)
        transcript = self._transcriber.transcribe(output_path)
        word_timestamps = [
            {"word": w.word, "start": w.start, "end": w.end} for w in transcript.words
        ]

        return VoiceoverResult(
            audio_path=output_path,
            duration_seconds=duration_seconds,
            word_timestamps=word_timestamps,
        )
