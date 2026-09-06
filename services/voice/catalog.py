"""Named voice presets shown in the UI's voice picker. These are labels a
video is tagged with (`Video.voice_preset` / `Settings.default_voice_preset`)
— not audio. No engine is configured yet (see services/voice/chatterbox),
so there is nothing to preview: picking a preset says "use this voice once
synthesis runs," it doesn't play a sample. Keep this list provider-agnostic
so it doesn't need to change if Chatterbox is swapped for something else.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class VoicePreset:
    id: str
    name: str
    description: str


VOICE_PRESETS: list[VoicePreset] = [
    VoicePreset(
        id="warm-narrator",
        name="Warm Narrator",
        description="Calm, storytelling pace. Explainers and documentary-style content.",
    ),
    VoicePreset(
        id="energetic-host",
        name="Energetic Host",
        description="Upbeat, fast-paced delivery. Listicles and hype content.",
    ),
    VoicePreset(
        id="calm-educator",
        name="Calm Educator",
        description="Clear, measured, instructional tone. Tutorials and how-tos.",
    ),
    VoicePreset(
        id="deep-authoritative",
        name="Deep & Authoritative",
        description="Serious, weighty delivery. News-style or high-stakes topics.",
    ),
    VoicePreset(
        id="friendly-casual",
        name="Friendly & Casual",
        description="Conversational and approachable, like talking to a friend.",
    ),
    VoicePreset(
        id="bright-upbeat",
        name="Bright & Upbeat",
        description="Light, cheerful energy. Lifestyle and quick-tip content.",
    ),
]

VOICE_PRESETS_BY_ID = {preset.id: preset for preset in VOICE_PRESETS}
