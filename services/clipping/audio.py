"""Pulls a transcription-ready audio track out of an uploaded source video.
Real local ffmpeg processing, same category as services/rendering/ffmpeg —
no cost, no approval gate."""

import subprocess

from services.rendering.ffmpeg.assembler import AssemblyError


def extract_audio_for_transcription(video_path: str, output_path: str) -> None:
    """16kHz mono PCM WAV — the input format faster-whisper expects."""
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            output_path,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssemblyError(f"ffmpeg audio extraction failed: {result.stderr}")
