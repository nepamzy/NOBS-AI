"""Builds burned-in captions from voiceover word_timestamps (CLAUDE.md:
Voice -> word timestamps -> subtitle generator -> styled captions -> FFmpeg).

One style only for V1 (plain, burned in via assembler.burn_in_captions) —
CLAUDE.md's eventual Minimal/YouTube/Bold/Cinematic/Highlight style picker
is future work, not required to get captions working end-to-end.
"""

from dataclasses import dataclass

MAX_WORDS_PER_CUE = 8
MAX_GAP_SECONDS = 0.6  # a pause this long starts a new cue, even under the word cap


@dataclass
class Cue:
    start_seconds: float
    end_seconds: float
    text: str


def build_cues(scene_word_timestamps: list[tuple[float, list[dict]]]) -> list[Cue]:
    """scene_word_timestamps: [(scene_start_offset_seconds, word_timestamps), ...]
    in scene order. Each word_timestamps entry is {"word","start","end"},
    timed relative to that scene's own voiceover — the offset shifts it onto
    the final assembled timeline, which lines up exactly because assembly
    already conformed each scene's clip to its own voiceover's real length.
    """
    cues: list[Cue] = []
    current_words: list[dict] = []
    current_offset = 0.0

    def flush() -> None:
        nonlocal current_words
        if current_words:
            cues.append(
                Cue(
                    start_seconds=current_offset + current_words[0]["start"],
                    end_seconds=current_offset + current_words[-1]["end"],
                    text=" ".join(w["word"] for w in current_words),
                )
            )
        current_words = []

    for offset, word_timestamps in scene_word_timestamps:
        flush()  # never blend narration across a scene boundary into one cue
        current_offset = offset
        for word in word_timestamps:
            if current_words and (
                len(current_words) >= MAX_WORDS_PER_CUE
                or word["start"] - current_words[-1]["end"] > MAX_GAP_SECONDS
            ):
                flush()
            current_words.append(word)
    flush()

    return cues


def render_srt(cues: list[Cue]) -> str:
    def timestamp(seconds: float) -> str:
        millis = round(seconds * 1000)
        hours, millis = divmod(millis, 3_600_000)
        minutes, millis = divmod(millis, 60_000)
        secs, millis = divmod(millis, 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    lines = []
    for i, cue in enumerate(cues, start=1):
        lines.append(str(i))
        lines.append(f"{timestamp(cue.start_seconds)} --> {timestamp(cue.end_seconds)}")
        lines.append(cue.text)
        lines.append("")
    return "\n".join(lines)
