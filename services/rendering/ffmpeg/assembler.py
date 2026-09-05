"""FFmpeg assembly (CLAUDE.md Part 3): scene clips + voiceover + music +
captions -> final MP4. Purely local processing of already-generated files —
no external calls, no cost — so unlike the AI/video/voice engines this one
is a real implementation, not a stub behind an approval gate.

Uses ffmpeg's concat demuxer for clips, then muxes in the voiceover audio.
Music mixing and burned-in captions are not implemented yet (CLAUDE.md build
order puts captions styling after core assembly) — calling those paths
raises NotImplementedError rather than silently skipping them.
"""

import subprocess
import tempfile
from pathlib import Path


class AssemblyError(RuntimeError):
    """Raised when the local ffmpeg invocation itself fails (bad input files,
    ffmpeg missing, etc.) — not a cost/approval issue, a processing failure."""


def concat_clips(clip_paths: list[str], output_path: str) -> None:
    if not clip_paths:
        raise AssemblyError("No clips provided to concatenate")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for path in clip_paths:
            f.write(f"file '{Path(path).resolve()}'\n")
        concat_list_path = f.name

    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_list_path,
                "-c", "copy",
                output_path,
            ],
            capture_output=True,
            text=True,
        )
    finally:
        Path(concat_list_path).unlink(missing_ok=True)

    if result.returncode != 0:
        raise AssemblyError(f"ffmpeg concat failed: {result.stderr}")


def mux_voiceover(video_path: str, audio_path: str, output_path: str) -> None:
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            output_path,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssemblyError(f"ffmpeg voiceover mux failed: {result.stderr}")


def burn_in_captions(video_path: str, subtitles_path: str, output_path: str) -> None:
    raise NotImplementedError("Caption styling (Minimal/YouTube/Bold/...) not yet implemented")
