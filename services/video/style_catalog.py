"""Named visual style presets for a video (`Video.style_preset` /
Settings.default_style_preset`). Like the voice catalog, these are labels
recorded now for the video engine to use later — Wan isn't configured, so
no clip has ever actually been generated in any of these styles. Keeping
this catalog means NOBS AI never has just one visual template: the storyboard
and eventual generation prompts can vary look/tone by style, not just topic.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class StylePreset:
    id: str
    name: str
    description: str
    accent_hex: str  # a swatch color for the picker UI, not a rendering parameter


STYLE_PRESETS: list[StylePreset] = [
    StylePreset(
        id="clean-minimal",
        name="Clean & Minimal",
        description="Simple compositions, lots of negative space, calm pacing.",
        accent_hex="#e5e7eb",
    ),
    StylePreset(
        id="bold-dynamic",
        name="Bold & Dynamic",
        description="High energy, punchy motion, vibrant saturated color.",
        accent_hex="#f97316",
    ),
    StylePreset(
        id="cinematic",
        name="Cinematic",
        description="Film-like framing, dramatic lighting, shallow depth of field.",
        accent_hex="#1e293b",
    ),
    StylePreset(
        id="documentary",
        name="Documentary",
        description="Realistic and grounded, natural lighting, handheld feel.",
        accent_hex="#78716c",
    ),
    StylePreset(
        id="playful-colorful",
        name="Playful & Colorful",
        description="Bright palette, illustrative feel, fun and energetic.",
        accent_hex="#ec4899",
    ),
]

STYLE_PRESETS_BY_ID = {preset.id: preset for preset in STYLE_PRESETS}
