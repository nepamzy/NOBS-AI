"""Small shared ffprobe helper — used anywhere a real measured duration is
needed (never an estimate), so it isn't reimplemented per caller."""

import subprocess

from services.rendering.ffmpeg.assembler import AssemblyError


def probe_duration_seconds(media_path: str) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            media_path,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssemblyError(f"ffprobe duration lookup failed: {result.stderr}")
    return float(result.stdout.strip())
