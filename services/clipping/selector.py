"""Picks N clip-worthy moments from a transcript using Claude, then snaps
each suggested boundary onto the nearest REAL word edge from the actual
transcript — the LLM's timestamps are a guess at best, never trusted
literally, exactly like the main pipeline never trusts the script
engine's duration *estimate* over a scene's *measured* voiceover length.
This is the "right audio" part: a clip can start/end on a word boundary
but never mid-word, because it's anchored to data faster-whisper actually
measured, not a number Claude typed.

Optionally also looks at sampled video frames (services/clipping/frames.py)
so selection isn't purely transcript-driven — a visually striking or funny
moment with little said can still get picked, and a flat visual over
exciting narration doesn't automatically win just because it was said
well. Frames are a hint toward WHICH moments to flag, same as the
transcript's [MM:SS] markers — the actual cut points still only ever
come from real transcript word edges.
"""

import base64
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from services.clipping.frames import FrameSample
from services.clipping.transcription.engine import TranscriptResult, Word
from services.common.errors import ApprovalRequiredError, CostWarning, EngineNotConfiguredError

_MAX_OUTPUT_TOKENS = 4096
_TIMESTAMP_MARKER_INTERVAL_SECONDS = 15


@dataclass
class ClipSelection:
    title: str
    reason: str
    start_seconds: float
    end_seconds: float


class _ClipSelectionModel(BaseModel):
    title: str
    reason: str
    start_seconds: float
    end_seconds: float


class _ClipSelectionsModel(BaseModel):
    clips: list[_ClipSelectionModel]


def _timestamped_transcript(words: list[Word]) -> str:
    """Plain text with a [MM:SS] marker inserted periodically, so the LLM
    can reference roughly where something was said. Precision comes later
    from snapping to the real word list, not from this string."""
    if not words:
        return ""
    lines = []
    next_marker_at = 0.0
    current_line: list[str] = []
    for word in words:
        if word.start >= next_marker_at:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = []
            minutes, seconds = divmod(int(word.start), 60)
            lines.append(f"[{minutes:02d}:{seconds:02d}]")
            next_marker_at = word.start + _TIMESTAMP_MARKER_INTERVAL_SECONDS
        current_line.append(word.word)
    if current_line:
        lines.append(" ".join(current_line))
    return " ".join(lines)


def _snap_to_word_boundary(target_seconds: float, words: list[Word], edge: str) -> float:
    """edge='start': snap to the start of the nearest word. edge='end':
    snap to the end of the nearest word. Never returns a time that falls
    inside a word, only at one of its two real edges."""
    if not words:
        return target_seconds
    key = (lambda w: w.start) if edge == "start" else (lambda w: w.end)
    closest = min(words, key=lambda w: abs(key(w) - target_seconds))
    return key(closest)


def _format_timestamp(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes:02d}:{secs:02d}"


def _build_message_content(
    transcript_text: str, target_count: int, frames: list[FrameSample]
) -> list[dict]:
    prompt_text = (
        f"Here is a timestamped transcript of a video "
        f"([MM:SS] markers every {_TIMESTAMP_MARKER_INTERVAL_SECONDS}s):\n\n"
        f"{transcript_text}\n\n"
    )
    if frames:
        prompt_text += (
            f"Below are {len(frames)} sample frames from the video, each "
            "labeled with its timestamp — use them to also judge what's "
            "visually happening, not just what's said (a strong visual "
            "moment can be worth clipping even with little dialogue, and "
            "a flat shot shouldn't win purely because the words were "
            "good).\n\n"
        )
    prompt_text += (
        f"Pick the {target_count} most compelling, self-contained "
        "moments for short clips — the kind worth clipping out on "
        "their own: a strong hook, a surprising or funny line, a "
        "concise insight, an emotional beat, or a striking visual. "
        "Each clip should make sense without the rest of the video. "
        "For each, give a short title, a one-sentence reason it's "
        "worth clipping, and an approximate start_seconds/end_seconds "
        "(use the [MM:SS] markers as your guide — exact second "
        "precision isn't needed, the system snaps your guess to "
        "the nearest real word boundary). Keep each clip "
        "between 15 and 90 seconds."
    )

    content: list[dict] = [{"type": "text", "text": prompt_text}]
    for frame in frames:
        content.append({"type": "text", "text": f"[{_format_timestamp(frame.timestamp)}] frame:"})
        image_data = base64.b64encode(Path(frame.path).read_bytes()).decode()
        content.append(
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": image_data},
            }
        )
    return content


def select_clips(
    transcript: TranscriptResult,
    target_count: int,
    llm_provider: str,
    llm_api_key: str,
    llm_model: str,
    frames: list[FrameSample] | None = None,
) -> list[ClipSelection]:
    frames = frames or []
    if not llm_provider or not llm_api_key:
        raise ApprovalRequiredError(
            CostWarning(
                action=f"Select {target_count} clip-worthy moments from an uploaded video",
                service="Anthropic API (unconfigured)",
                expected_cost="COST UNKNOWN — no LLM_PROVIDER/LLM_API_KEY set",
                billing_type="per token",
                max_expected_cost="A few thousand input tokens for the "
                "transcript plus a short structured output — well under "
                "$1 at current Claude pricing for most videos. If sample "
                "frames are attached, each small (480px-wide) frame adds "
                "roughly a couple hundred more image tokens, still well "
                "under $1 total for the default frame cap — re-verify "
                "before relying on this figure",
                risk="Low",
                why_needed="Picking compelling clips from a transcript "
                "(and, when available, sampled video frames) requires an "
                "LLM call — this is the same LLM connection already used "
                "for script/research generation and the admin assistant.",
            )
        )
    if llm_provider != "anthropic":
        raise EngineNotConfiguredError(
            f"LLM_PROVIDER={llm_provider!r} is not implemented — only 'anthropic' is wired up."
        )

    import anthropic

    client = anthropic.Anthropic(api_key=llm_api_key)
    transcript_text = _timestamped_transcript(transcript.words)
    content = _build_message_content(transcript_text, target_count, frames)

    response = client.messages.parse(
        model=llm_model,
        max_tokens=_MAX_OUTPUT_TOKENS,
        messages=[{"role": "user", "content": content}],
        output_format=_ClipSelectionsModel,
    )
    parsed = response.parsed_output

    selections = []
    for clip in parsed.clips:
        start = _snap_to_word_boundary(clip.start_seconds, transcript.words, "start")
        end = _snap_to_word_boundary(clip.end_seconds, transcript.words, "end")
        if end <= start:
            continue  # a degenerate snap (e.g. both guesses landed on the same word) — skip it
        selections.append(
            ClipSelection(
                title=clip.title, reason=clip.reason, start_seconds=start, end_seconds=end
            )
        )
    return selections
