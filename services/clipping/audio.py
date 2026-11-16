"""Pulls a transcription-ready audio track out of an uploaded source video.
Real local ffmpeg processing, same category as services/rendering/ffmpeg —
no cost, no approval gate."""

import subprocess

from services.rendering.ffmpeg.assembler import AssemblyError

NO_AUDIO_MESSAGE = (
    "This video has no audio track, so there is nothing to transcribe. Smart Clipping "
    "picks moments from what is said, so it needs a video with sound. Delete this upload "
    "and upload one that has audio."
)


def has_audio_stream(video_path: str) -> bool:
    """False only when ffprobe positively finds no audio stream. If the file
    can't be inspected for any reason, answer True and let the real extraction
    report whatever is actually wrong."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=index", "-of", "csv=p=0", video_path],
            capture_output=True, text=True, timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired):
        return True
    if result.returncode != 0:
        return True
    return bool(result.stdout.strip())


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
