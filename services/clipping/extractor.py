"""Cuts one clip out of a source video and (optionally) burns in captions
built from the real transcript words that fall inside it — reuses
services/rendering/ffmpeg's existing caption pipeline rather than
reinventing it. Real local ffmpeg processing, no cost."""

import subprocess
from pathlib import Path

from services.rendering.ffmpeg.assembler import AssemblyError, burn_in_captions
from services.rendering.ffmpeg.captions import build_cues, render_srt


def extract_clip(
    source_path: str, start_seconds: float, end_seconds: float, output_path: str
) -> None:
    duration = end_seconds - start_seconds
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-ss", str(start_seconds),
            "-i", source_path,
            "-t", str(duration),
            "-c:v", "libx264",
            "-c:a", "aac",
            output_path,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssemblyError(f"ffmpeg clip extraction failed: {result.stderr}")


def caption_clip(clip_path: str, clip_words: list[dict], output_path: str, tmp_dir: str) -> None:
    """clip_words: word_timestamps already shifted onto the CLIP's own
    timeline (i.e. clip-relative, starting near 0) — see pipeline.py."""
    cues = build_cues([(0.0, clip_words)])
    srt_content = render_srt(cues)
    subtitles_path = Path(tmp_dir) / f"{Path(clip_path).stem}.srt"
    subtitles_path.write_text(srt_content)
    burn_in_captions(clip_path, str(subtitles_path), output_path)
