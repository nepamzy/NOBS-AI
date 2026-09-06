"""Picks a background-music track from a folder Nobert curates himself —
YouTube Audio Library has no public API to pull tracks automatically (see
chat history), so this is manual-download-once, then rotate automatically.

Avoids repeating the same track across an owner's recent videos, the same
anti-template instinct behind the Style picker: pick something used least
recently, and only reuse one at all once every other track in the library
has been used at least as recently (never blocks a video over this — an
empty or fully-cycled library just means "no music this time" or "reuse
the least-stale option", never a pipeline failure).
"""

import random
from pathlib import Path

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}


def list_available_tracks(library_path: str) -> list[str]:
    root = Path(library_path)
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.suffix.lower() in AUDIO_EXTENSIONS)


def pick_track(library_path: str, recently_used: list[str]) -> str | None:
    """recently_used: track filenames from this owner's most recent videos,
    most recent first. Returns a filename (not a path) to mix in, or None if
    the library has nothing in it yet."""
    available = list_available_tracks(library_path)
    if not available:
        return None

    unused = [t for t in available if t not in recently_used]
    if unused:
        return random.choice(unused)

    # every track has been used recently (a small library, or a long run of
    # videos) — reuse is unavoidable, so pick whichever was used longest ago
    # rather than the most recent repeat
    for track in reversed(recently_used):
        if track in available:
            return track
    return random.choice(available)
