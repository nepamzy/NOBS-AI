"""RQ task entry points. Runs inside the worker process (apps/worker), not
the API process — the API only ever enqueues (see app/jobs/queue.py)."""

import logging
import uuid

from app.config import settings
from app.db import SessionLocal
from app.engines import get_script_engine
from services.ai.orchestration.pipeline import PipelineBlocked, PipelineContext, advance_one_stage
from services.ai.research.engine import ResearchEngine
from services.storage.factory import get_storage_backend
from services.video.factory import get_video_engine
from services.voice.factory import get_voice_engine


logger = logging.getLogger(__name__)


def _record_failure(video_id: str, stage_before: str, exc: Exception) -> None:
    """Mark a video FAILED on a brand-new DB session. The job's own session may
    be the thing that just broke (e.g. Supabase dropped the SSL connection
    mid-call), so reusing it here left videos stuck 'In Progress' forever."""
    from app.models.enums import PipelineStage
    from app.models.video import Video

    fresh = SessionLocal()
    try:
        video = fresh.get(Video, uuid.UUID(video_id))
        if video is None:
            return
        video.stage = PipelineStage.FAILED
        video.stage_detail = f"Crashed at '{stage_before}': {type(exc).__name__}: {exc}"
        fresh.commit()
    except Exception:
        logger.exception("Could not record failure for video %s", video_id)
        fresh.rollback()
    finally:
        fresh.close()


def _build_context(db) -> PipelineContext:
    from app.pipeline_test_mode import get_enabled

    return PipelineContext(
        research_engine=ResearchEngine(
            settings.llm_provider, settings.llm_api_key, settings.llm_model
        ),
        script_engine=get_script_engine(),
        voice_engine=get_voice_engine(
            settings.voice_provider,
            settings.chatterbox_api_url,
            settings.elevenlabs_api_key,
            settings.elevenlabs_voice_map,
            settings.chatterbox_voice_map,
        ),
        video_engine=get_video_engine(
            settings.video_provider,
            settings.runpod_api_key,
            settings.wan_endpoint_id,
            settings.local_wan_api_url,
        ),
        storage_root=settings.local_storage_root,
        test_no_audio=get_enabled(db),
        music_library_path=settings.music_library_path,
        storage_backend=get_storage_backend(
            settings.storage_backend,
            settings.supabase_url,
            settings.supabase_service_role_key,
            settings.supabase_storage_bucket,
        ),
    )


_MAX_STAGES_PER_JOB = 12  # safety cap against an accidental infinite loop — 10
# real stages plus headroom for the one extra "blocked, then auto-approved"
# pass an auto_publish video takes at STORYBOARD_REVIEW


def _auto_publish_to_youtube(video, db) -> str:
    """Only reached when video.auto_publish is True — Nobert's own
    deliberate opt-in (see app/models/upload_schedule.py), never the
    default. Failures here never undo the finished video; they're just
    noted on stage_detail so he can upload/publish by hand instead."""
    from app.models.script import Script
    from app.routers.videos import publish_to_youtube, upload_to_youtube
    from app.schemas.youtube import YouTubeUploadRequest
    from services.common.errors import EngineNotConfiguredError

    owner = video.project.owner
    script = db.query(Script).filter(Script.video_id == video.id).one_or_none()
    title = script.title if script else video.topic
    description = script.hook if script else video.topic

    try:
        upload_to_youtube(
            video.id,
            YouTubeUploadRequest(title=title, description=description),
            db=db,
            user=owner,
        )
        publish_to_youtube(video.id, db=db, user=owner)
    except EngineNotConfiguredError as exc:
        video.stage_detail = f"Auto-publish skipped — YouTube not configured: {exc}"
        db.commit()
        return "auto-publish skipped: YouTube not configured"
    except Exception as exc:  # noqa: BLE001 - a failed upload must not fail the whole job
        video.stage_detail = f"Auto-publish failed: {exc}"
        db.commit()
        return f"auto-publish failed: {exc}"

    return "auto-published to YouTube"


def advance_pipeline(video_id: str, run_research: bool) -> str:
    """Drive a Video forward through as many stages as it can complete
    unattended, stopping the moment it hits something that needs Nobert:
    an approval-gated engine call, or the storyboard-review checkpoint.
    Returns a short status string for the RQ job result.

    A PipelineBlocked is expected, normal behavior — it's reported, not
    raised as a job failure, so RQ doesn't retry-storm a call that will
    never succeed without Nobert's action. The ONE exception is the
    storyboard-review block on a video with auto_publish=True (Nobert's
    own explicit opt-in per schedule, off by default) — that one gets
    auto-approved and the loop continues, instead of stopping.
    """
    db = SessionLocal()
    try:
        from app.models.enums import PipelineStage
        from app.models.video import Video

        video = db.get(Video, uuid.UUID(video_id))
        if video is None:
            return f"video {video_id} not found"

        ctx = _build_context(db)
        terminal = {PipelineStage.COMPLETED, PipelineStage.FAILED}
        for _ in range(_MAX_STAGES_PER_JOB):
            if video.stage in terminal:
                break
            stage_before = video.stage.value
            try:
                advance_one_stage(video, db, ctx, run_research=run_research)
            except PipelineBlocked as blocked:
                if blocked.stage == "storyboard_review" and video.auto_publish:
                    video.storyboard_approved = True
                    video.stage_detail = "Auto-approved (schedule automation active)"
                    db.commit()
                    continue
                return f"blocked at {blocked.stage}: {blocked.reason}"
            except Exception as exc:
                # Anything unexpected used to leave the video silently stuck at
                # its last stage with no reason shown. Record it as FAILED with
                # the real error so the page says what happened and Restart works.
                logger.exception("Pipeline crashed at stage %s for video %s", stage_before, video_id)
                _record_failure(video_id, stage_before, exc)
                return f"failed at {stage_before}: {exc}"

        ready_to_auto_publish = (
            video.stage == PipelineStage.COMPLETED
            and video.auto_publish
            and not video.youtube_video_id
        )
        if ready_to_auto_publish:
            publish_result = _auto_publish_to_youtube(video, db)
            return f"{video.stage.value}; {publish_result}"

        if video.stage in terminal:
            return f"{video.stage.value}"
        return f"reached {video.stage.value} (stage limit for one job run)"
    finally:
        db.close()
