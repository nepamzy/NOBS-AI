"""RQ task entry points for the clipping pipeline — mirrors
apps/api/app/jobs/tasks.py's shape for the main video pipeline."""

import logging
import uuid

from app.config import settings
from app.db import SessionLocal
from services.clipping.pipeline import ClipPipelineBlocked, ClipPipelineContext, advance_clip_stage
from services.clipping.transcription.factory import get_transcription_engine
from services.storage.factory import get_storage_backend

logger = logging.getLogger(__name__)

_MAX_STAGES_PER_JOB = 6  # UPLOADED, TRANSCRIBING, SELECTING_CLIPS, EXTRACTING + headroom


def _record_clip_failure(source_video_id: str, stage_before: str, exc: Exception) -> None:
    """Mark a source video FAILED on a brand-new DB session — same reasoning
    as app/jobs/tasks.py's _record_failure: the job's own session may be
    the thing that just broke. Without this, an unexpected crash left the
    row stuck at its last stage forever with no reason shown anywhere."""
    from app.models.enums import ClipJobStage
    from app.models.source_video import SourceVideo

    fresh = SessionLocal()
    try:
        source_video = fresh.get(SourceVideo, uuid.UUID(source_video_id))
        if source_video is None:
            return
        source_video.stage = ClipJobStage.FAILED
        source_video.stage_detail = f"Crashed at '{stage_before}': {type(exc).__name__}: {exc}"
        fresh.commit()
    except Exception:
        logger.exception("Could not record failure for source video %s", source_video_id)
        fresh.rollback()
    finally:
        fresh.close()


def _build_clip_context() -> ClipPipelineContext:
    return ClipPipelineContext(
        transcription_engine=get_transcription_engine(
            settings.transcription_provider, settings.whisper_model_size
        ),
        llm_provider=settings.llm_provider,
        llm_api_key=settings.llm_api_key,
        llm_model=settings.llm_model,
        storage_root=settings.local_storage_root,
        storage_backend=get_storage_backend(
            settings.storage_backend,
            settings.supabase_url,
            settings.supabase_service_role_key,
            settings.supabase_storage_bucket,
        ),
    )


def _auto_publish_clips_to_youtube(source_video, db) -> str:
    """Only reached when source_video.auto_publish is True — defaults True
    for this feature specifically (Nobert's own instruction: give it a
    video, it ships), unlike every other auto-publish flag in this app.
    One failed clip upload never blocks the others."""
    from app.models.clip import Clip
    from services.common.errors import EngineNotConfiguredError
    from services.connectors.youtube.adapter import YouTubeConnector

    youtube = YouTubeConnector(
        settings.clips_youtube_client_id,
        settings.clips_youtube_client_secret,
        settings.clips_youtube_refresh_token,
    )

    clips = (
        db.query(Clip)
        .filter(Clip.source_video_id == source_video.id, Clip.clip_path.isnot(None))
        .all()
    )
    results = []
    for clip in clips:
        if clip.youtube_published:
            continue
        try:
            if not clip.youtube_video_id:
                result = youtube.upload_video(clip.clip_path, clip.title, clip.reason)
                clip.youtube_video_id = result.video_id
                db.commit()
            youtube.publish_video(clip.youtube_video_id)
            clip.youtube_published = True
            db.commit()
            results.append(f"clip {clip.id}: published")
        except EngineNotConfiguredError as exc:
            source_video.stage_detail = f"Auto-publish skipped — YouTube not configured: {exc}"
            db.commit()
            return "auto-publish skipped: clips YouTube channel not configured"
        except Exception as exc:  # noqa: BLE001 - one failed clip must not fail the whole job
            db.rollback()
            results.append(f"clip {clip.id}: failed ({exc})")

    return "; ".join(results) if results else "no clips to publish"


def advance_clip_pipeline(source_video_id: str) -> str:
    db = SessionLocal()
    try:
        from app.models.enums import ClipJobStage
        from app.models.source_video import SourceVideo

        source_video = db.get(SourceVideo, uuid.UUID(source_video_id))
        if source_video is None:
            return f"source video {source_video_id} not found"

        ctx = _build_clip_context()
        terminal = {ClipJobStage.COMPLETED, ClipJobStage.FAILED}
        for _ in range(_MAX_STAGES_PER_JOB):
            if source_video.stage in terminal:
                break
            stage_before = source_video.stage.value
            try:
                advance_clip_stage(source_video, db, ctx)
            except ClipPipelineBlocked as blocked:
                return f"blocked at {blocked.stage}: {blocked.reason}"
            except Exception as exc:
                # Anything unexpected used to leave the source video silently
                # stuck at its last stage with no reason shown anywhere.
                # Record it as FAILED with the real error instead.
                logger.exception(
                    "Clip pipeline crashed at stage %s for source video %s",
                    stage_before,
                    source_video_id,
                )
                _record_clip_failure(source_video_id, stage_before, exc)
                return f"failed at {stage_before}: {exc}"

        if source_video.stage == ClipJobStage.COMPLETED and source_video.auto_publish:
            publish_result = _auto_publish_clips_to_youtube(source_video, db)
            return f"{source_video.stage.value}; {publish_result}"

        if source_video.stage in terminal:
            return f"{source_video.stage.value}"
        return f"reached {source_video.stage.value} (stage limit for one job run)"
    finally:
        db.close()
