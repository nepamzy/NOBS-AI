"""Drives a SourceVideo through:

    UPLOADED -> TRANSCRIBING -> SELECTING_CLIPS -> EXTRACTING -> COMPLETED

One call advances by exactly one stage, mirroring
services/ai/orchestration/pipeline.py's design. Transcription is free local
compute (no block possible there beyond a missing dependency); clip
selection calls the LLM and can block exactly like the main pipeline's
SCRIPT stage. There is no review/approval stage in this pipeline the way
STORYBOARD_REVIEW gates the main one — Nobert's own instruction for this
feature was "give it a video, it ships automatically" (SourceVideo.auto_
publish defaults True). Publishing each clip to the second YouTube channel
happens OUTSIDE this file, in apps/api/app/jobs/clip_tasks.py, once this
pipeline reaches COMPLETED — same separation as the main pipeline keeps
between "finish the video" and "touch YouTube".
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from services.clipping.transcription.engine import TranscriptionEngine, TranscriptResult, Word
from services.common.errors import ApprovalRequiredError, EngineNotConfiguredError
from services.storage.backend import LocalStorageBackend, StorageBackend


@dataclass
class ClipPipelineContext:
    transcription_engine: TranscriptionEngine
    llm_provider: str
    llm_api_key: str
    llm_model: str
    storage_root: str
    storage_backend: StorageBackend = field(default_factory=LocalStorageBackend)


class ClipPipelineBlocked(RuntimeError):
    def __init__(self, stage: str, reason: str):
        self.stage = stage
        self.reason = reason
        super().__init__(f"Clip pipeline blocked at stage '{stage}': {reason}")


def _block(source_video, db: Session, stage: str, reason: str) -> None:
    source_video.stage_detail = reason
    db.commit()
    raise ClipPipelineBlocked(stage, reason)


def _write_transcript(transcript: TranscriptResult, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "full_text": transcript.full_text,
        "words": [{"word": w.word, "start": w.start, "end": w.end} for w in transcript.words],
    }
    Path(path).write_text(json.dumps(payload))


def _read_transcript(path: str) -> TranscriptResult:
    payload = json.loads(Path(path).read_text())
    words = [Word(word=w["word"], start=w["start"], end=w["end"]) for w in payload["words"]]
    return TranscriptResult(full_text=payload["full_text"], words=words)


def advance_clip_stage(source_video, db: Session, ctx: ClipPipelineContext) -> None:
    from app.models.clip import Clip
    from app.models.enums import ClipJobStage

    from services.clipping.audio import extract_audio_for_transcription
    from services.clipping.extractor import caption_clip, extract_clip
    from services.clipping.selector import select_clips

    stage = source_video.stage
    output_dir = Path(ctx.storage_root) / "clips" / str(source_video.id)
    output_dir.mkdir(parents=True, exist_ok=True)

    if stage == ClipJobStage.UPLOADED:
        audio_path = str(output_dir / "audio.wav")
        extract_audio_for_transcription(source_video.source_path, audio_path)

        try:
            transcript = ctx.transcription_engine.transcribe(audio_path)
        except EngineNotConfiguredError as exc:
            _block(source_video, db, "transcribing", str(exc))
            return

        transcript_path = str(output_dir / "transcript.json")
        _write_transcript(transcript, transcript_path)
        source_video.transcript_path = transcript_path
        source_video.stage = ClipJobStage.TRANSCRIBING
        source_video.stage_detail = ""
        db.commit()
        return

    if stage == ClipJobStage.TRANSCRIBING:
        # Transcription already happened above; this stage's only job is
        # to hand off to clip selection — kept separate so stage_detail/
        # progress reporting has a dedicated "transcribing" state to show
        # in the UI while a long video is still being processed.
        source_video.stage = ClipJobStage.SELECTING_CLIPS
        db.commit()
        return

    if stage == ClipJobStage.SELECTING_CLIPS:
        transcript = _read_transcript(source_video.transcript_path)

        try:
            selections = select_clips(
                transcript,
                source_video.target_clip_count,
                ctx.llm_provider,
                ctx.llm_api_key,
                ctx.llm_model,
            )
        except ApprovalRequiredError as exc:
            _block(source_video, db, "selecting_clips", exc.cost_warning.render())
            return

        for selection in selections:
            db.add(
                Clip(
                    source_video_id=source_video.id,
                    start_seconds=selection.start_seconds,
                    end_seconds=selection.end_seconds,
                    title=selection.title,
                    reason=selection.reason,
                )
            )
        source_video.stage = ClipJobStage.EXTRACTING
        source_video.stage_detail = ""
        db.commit()
        return

    if stage == ClipJobStage.EXTRACTING:
        transcript = _read_transcript(source_video.transcript_path)
        clips = db.query(Clip).filter(Clip.source_video_id == source_video.id).all()

        for clip in clips:
            if clip.clip_path:
                continue  # already extracted on a previous (partial) run
            raw_path = str(output_dir / f"{clip.id}_raw.mp4")
            extract_clip(source_video.source_path, clip.start_seconds, clip.end_seconds, raw_path)

            clip_words = [
                {
                    "word": w.word,
                    "start": w.start - clip.start_seconds,
                    "end": w.end - clip.start_seconds,
                }
                for w in transcript.words
                if clip.start_seconds <= w.start < clip.end_seconds
            ]
            captioned_path = str(output_dir / f"{clip.id}.mp4")
            if clip_words:
                caption_clip(raw_path, clip_words, captioned_path, str(output_dir))
            else:
                captioned_path = raw_path

            clip.clip_path = ctx.storage_backend.upload(
                captioned_path, f"clips/{source_video.id}/{clip.id}.mp4"
            )

        source_video.stage = ClipJobStage.COMPLETED
        source_video.stage_detail = ""
        db.commit()
        return

    if stage == ClipJobStage.COMPLETED:
        return

    _block(source_video, db, stage.value, "No handler for this stage")
