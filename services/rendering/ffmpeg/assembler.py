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


def conform_clip_to_duration(clip_path: str, target_seconds: float, output_path: str) -> None:
    """Makes a scene's clip exactly as long as that scene's real (measured)
    voiceover — never by changing playback speed, which is what makes a
    video feel like it's lagging behind or rushing ahead of its narration.
    A clip longer than the voiceover is trimmed; a shorter one is extended
    by holding its last frame. Doing this per scene, before concatenation,
    is what lets assembly just concatenate + mux with no drift to correct
    for later — there's nothing left to cut and join by hand.
    """
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", clip_path,
            "-vf", f"tpad=stop_mode=clone:stop_duration={target_seconds + 1}",
            "-t", str(target_seconds),
            "-an",
            output_path,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssemblyError(f"ffmpeg duration-conform failed: {result.stderr}")


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
    """Burns an .srt onto the video (single plain style for V1 — see
    services/rendering/ffmpeg/captions.py). Selectable styles
    (Minimal/YouTube/Bold/Cinematic/Highlight, per CLAUDE.md) are future
    work; this gets captions on screen at all."""
    style = (
        "FontSize=20,PrimaryColour=&HFFFFFF,BorderStyle=3,Outline=0,"
        "Shadow=0,BackColour=&H80000000"
    )
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"subtitles={subtitles_path}:force_style='{style}'",
            "-c:a", "copy",
            output_path,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssemblyError(f"ffmpeg caption burn-in failed: {result.stderr}")


def extract_frame(video_path: str, timestamp_seconds: float, output_path: str) -> None:
    """Pulls a single frame from a finished video as a thumbnail candidate —
    no separate paid image-generation step needed for a V1 A/B/C thumbnail
    picker (CLAUDE.md Part 3 — Thumbnail generation)."""
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-ss", str(timestamp_seconds),
            "-i", video_path,
            "-vframes", "1",
            output_path,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssemblyError(f"ffmpeg frame extraction failed: {result.stderr}")
