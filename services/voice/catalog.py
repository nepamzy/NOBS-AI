"""Named voice presets shown in the UI's voice picker. These are labels a
video is tagged with (`Video.voice_preset` / `Settings.default_voice_preset`)
— not the engine that will actually narrate a video. No synthesis engine is
configured yet (see services/voice/chatterbox), so picking a preset doesn't
change what generation does; it's a label recorded for when it can.

`preview_path` is different: it's a short pre-recorded sample (ElevenLabs,
one-time, ~$0.04 total for all 5 — see apps/web/public/voice-previews/) so
Nobert can hear roughly what a voice sounds like before picking. It is NOT
what will actually narrate the video — that still depends on whichever
engine gets configured later (Chatterbox, or ElevenLabs for real if that
becomes the chosen provider) and could sound different.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class VoicePreset:
    id: str
    name: str
    description: str
    preview_path: str | None = None


VOICE_PRESETS: list[VoicePreset] = [
    VoicePreset(
        id="warm-narrator",
        name="Warm Narrator",
        description="Calm, storytelling pace. Explainers and documentary-style content.",
        preview_path="/voice-previews/warm-narrator.mp3",
    ),
    VoicePreset(
        id="energetic-host",
        name="Energetic Host",
        description="Upbeat, fast-paced delivery. Listicles and hype content.",
        preview_path="/voice-previews/energetic-host.mp3",
    ),
    VoicePreset(
        id="calm-educator",
        name="Calm Educator",
        description="Clear, measured, instructional tone. Tutorials and how-tos.",
        preview_path="/voice-previews/calm-educator.mp3",
    ),
    VoicePreset(
        id="deep-authoritative",
        name="Deep & Authoritative",
        description="Serious, weighty delivery. News-style or high-stakes topics.",
        preview_path="/voice-previews/deep-authoritative.mp3",
    ),
    VoicePreset(
        id="friendly-casual",
        name="Friendly & Casual",
        description="Conversational and approachable, like talking to a friend.",
        preview_path="/voice-previews/friendly-casual.mp3",
    ),
]

VOICE_PRESETS_BY_ID = {preset.id: preset for preset in VOICE_PRESETS}
