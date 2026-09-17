"""RQ task entry points. Runs inside the worker process (apps/worker), not
the API process — the API only ever enqueues (see app/jobs/queue.py)."""

import uuid

from app.config import settings
from app.db import SessionLocal
from app.engines import get_script_engine
from services.ai.orchestration.pipeline import PipelineBlocked, PipelineContext, advance_one_stage
from services.ai.research.engine import ResearchEngine
from services.storage.factory import get_storage_backend
from services.video.wan.adapter import WanEngine
from services.voice.factory import get_voice_engine


def _build_context() -> PipelineContext:
    return PipelineContext(
        research_engine=ResearchEngine(settings.llm_provider, settings.llm_api_key),
        script_engine=get_script_engine(),
        voice_engine=get_voice_engine(
            settings.voice_provider,
            settings.chatterbox_api_url,
            settings.elevenlabs_api_key,
            settings.elevenlabs_voice_map,
        ),
        video_engine=WanEngine(settings.runpod_api_key, settings.wan_endpoint_id),
        storage_root=settings.local_storage_root,
        music_library_path=settings.music_library_path,
        storage_backend=get_storage_backend(
            settings.storage_backend,
            settings.supabase_url,
            settings.supabase_service_role_key,
            settings.supabase_storage_bucket,
        ),
    )


_MAX_STAGES_PER_JOB = 10  # safety cap against an accidental infinite loop


def advance_pipeline(video_id: str, run_research: bool) -> str:
    """Drive a Video forward through as many stages as it can complete
    unattended, stopping the moment it hits something that needs Nobert:
    an approval-gated engine call, or the storyboard-review checkpoint.
    Returns a short status string for the RQ job result.

    A PipelineBlocked is expected, normal behavior — it's reported, not
    raised as a job failure, so RQ doesn't retry-storm a call that will
    never succeed without Nobert's action.
    """
    db = SessionLocal()
    try:
        from app.models.enums import PipelineStage
        from app.models.video import Video

        video = db.get(Video, uuid.UUID(video_id))
        if video is None:
            return f"video {video_id} not found"

        ctx = _build_context()
        terminal = {PipelineStage.COMPLETED, PipelineStage.FAILED}
        for _ in range(_MAX_STAGES_PER_JOB):
            if video.stage in terminal:
                break
            try:
                advance_one_stage(video, db, ctx, run_research=run_research)
            except PipelineBlocked as blocked:
                return f"blocked at {blocked.stage}: {blocked.reason}"

        if video.stage in terminal:
            return f"{video.stage.value}"
        return f"reached {video.stage.value} (stage limit for one job run)"
    finally:
        db.close()
