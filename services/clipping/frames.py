"""Samples frames from a source video at a fixed interval so clip selection
can look at what's actually on screen, not just what's said. Real local
ffmpeg processing, same category as audio.py — no cost, no approval gate.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path

from services.rendering.ffmpeg.assembler import AssemblyError

# Caps how many frames ever get attached to one LLM call — a smarter clip
# pick isn't worth an unbounded image-token bill on a long video.
_MAX_FRAMES = 40
_DEFAULT_INTERVAL_SECONDS = 15.0
# Downscaled before sending to the LLM — plenty to judge "what's on screen"
# from, at a small fraction of the image-token cost of the source resolution.
_SAMPLE_WIDTH = 480


@dataclass
class FrameSample:
    timestamp: float
    path: str


def _probe_duration_seconds(video_path: str) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssemblyError(f"ffprobe duration lookup failed: {result.stderr}")
    return float(result.stdout.strip())


def extract_sample_frames(
    video_path: str, output_dir: str, interval_seconds: float = _DEFAULT_INTERVAL_SECONDS
) -> list[FrameSample]:
    """One frame every `interval_seconds`, widened automatically if that
    would exceed _MAX_FRAMES for a long video."""
    duration = _probe_duration_seconds(video_path)
    if duration <= 0:
        return []
    frame_count = max(1, int(duration // interval_seconds) + 1)
    if frame_count > _MAX_FRAMES:
        interval_seconds = duration / _MAX_FRAMES

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    pattern = str(Path(output_dir) / "frame_%05d.jpg")
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"fps=1/{interval_seconds},scale={_SAMPLE_WIDTH}:-1",
            "-q:v", "4",
            pattern,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssemblyError(f"ffmpeg frame sampling failed: {result.stderr}")

    frames = []
    for i, frame_path in enumerate(sorted(Path(output_dir).glob("frame_*.jpg"))):
        frames.append(FrameSample(timestamp=i * interval_seconds, path=str(frame_path)))
    return frames
