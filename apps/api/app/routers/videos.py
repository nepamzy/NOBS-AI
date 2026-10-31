import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.config import settings
from app.db import get_db
from app.engines import get_script_engine
from app.jobs.queue import enqueue_pipeline_start
from app.models.asset import Asset
from app.models.compliance import ComplianceReport
from app.models.enums import JobStatus, PipelineStage, UserRole
from app.models.project import Project
from app.models.script import Scene, Script
from app.models.user import User
from app.models.video import Video
from app.models.video_clip import VideoClip
from app.models.video_feedback import VideoFeedback
from app.schemas.asset import AssetRead
from app.schemas.script import SceneRead, SceneRegenerateRequest, SceneUpdate, ScriptRead
from app.schemas.video import ClipRecoverRequest, VideoCreate, VideoRead
from app.schemas.video_feedback import VideoFeedbackCreate, VideoFeedbackRead
from app.schemas.youtube import YouTubeUploadRequest
from services.ai.script.engine import SceneDraft
from services.common.errors import ApprovalRequiredError, EngineNotConfiguredError
from services.connectors.youtube.adapter import YouTubeConnector

router = APIRouter(prefix="/videos", tags=["videos"])


def _owned_project_or_404(db: Session, project_id: uuid.UUID, user: User) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _owned_video_or_404(db: Session, video_id: uuid.UUID, user: User) -> Video:
    video = (
        db.query(Video)
        .join(Project, Project.id == Video.project_id)
        .filter(Video.id == video_id, Project.owner_id == user.id)
        .one_or_none()
    )
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.post("", response_model=VideoRead, status_code=201)
def create_video(
    payload: VideoCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Video:
    _owned_project_or_404(db, payload.project_id, user)

    # Token balance is a placeholder unit standing in for real payment
    # (not built yet) — ADMIN (Nobert) is exempt entirely; every other user
    # spends one token per video created, checked and deducted atomically
    # with the video row so a race can't create two videos off one token.
    if user.role != UserRole.ADMIN:
        if user.token_balance <= 0:
            raise HTTPException(status_code=402, detail="No tokens remaining — contact the admin")
        user.token_balance -= 1

    video = Video(
        project_id=payload.project_id,
        topic=payload.topic,
        target_duration_seconds=payload.target_duration_seconds,
        voice_preset=payload.voice_preset,
        style_preset=payload.style_preset,
        stage=PipelineStage.TOPIC,
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    if payload.own_scenes:
        # "I already have a script" — write it straight to the DB and park
        # at STORYBOARD_REVIEW. No job is enqueued: RESEARCH and SCRIPT are
        # real LLM calls, and there is nothing for either to do when Nobert
        # already wrote the scenes himself — enqueueing here would silently
        # re-run (and re-bill) both stages for no reason.
        script = Script(
            video_id=video.id,
            title=payload.script_title.strip() or payload.topic[:500],
            hook=payload.script_hook.strip(),
            estimated_duration_seconds=sum(s.duration_seconds for s in payload.own_scenes),
            word_count=sum(len(s.narration.split()) for s in payload.own_scenes),
        )
        script.scenes = [
            Scene(
                order=i + 1,
                narration=s.narration.strip(),
                visual_prompt=s.visual_prompt.strip(),
                duration_seconds=s.duration_seconds,
                transition=s.transition,
            )
            for i, s in enumerate(payload.own_scenes)
        ]
        db.add(script)
        video.stage = PipelineStage.STORYBOARD_REVIEW
        video.stage_detail = "Awaiting storyboard approval"
        db.commit()
        db.refresh(video)
        return video

    # Hands off to the job queue immediately — the API never blocks on
    # research/script generation (CLAUDE.md: Job/queue system — critical).
    enqueue_pipeline_start(video_id=video.id, run_research=payload.run_research)

    return video


@router.get("", response_model=list[VideoRead])
def list_videos(
    project_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Video]:
    query = db.query(Video).join(Project, Project.id == Video.project_id).filter(
        Project.owner_id == user.id
    )
    if project_id is not None:
        query = query.filter(Video.project_id == project_id)
    return query.order_by(Video.created_at.desc()).all()


@router.get("/{video_id}", response_model=VideoRead)
def get_video(
    video_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Video:
    return _owned_video_or_404(db, video_id, user)


@router.get("/{video_id}/script", response_model=ScriptRead)
def get_video_script(
    video_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Script:
    _owned_video_or_404(db, video_id, user)
    script = db.query(Script).filter(Script.video_id == video_id).one_or_none()
    if script is None:
        raise HTTPException(status_code=404, detail="Script not generated yet")
    return script


@router.patch("/{video_id}/scenes/{scene_id}", response_model=SceneRead)
def update_scene(
    video_id: uuid.UUID,
    scene_id: uuid.UUID,
    payload: SceneUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Scene:
    """The "Edit" action on a storyboard scene (CLAUDE.md: Regenerate / Edit /
    Approve). Only allowed before storyboard approval — once approved, a
    scene is what gets sent to paid generation, so it shouldn't shift under
    a job that may already be running."""
    video = _owned_video_or_404(db, video_id, user)
    script = db.query(Script).filter(Script.video_id == video_id).one_or_none()
    if script is None:
        raise HTTPException(status_code=404, detail="Script not generated yet")

    scene = db.get(Scene, scene_id)
    if scene is None or scene.script_id != script.id:
        raise HTTPException(status_code=404, detail="Scene not found on this video")

    if video.storyboard_approved:
        raise HTTPException(
            status_code=409, detail="Storyboard already approved — scene is no longer editable"
        )

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(scene, field, value)
    db.commit()
    db.refresh(scene)
    return scene


@router.post("/{video_id}/scenes/{scene_id}/regenerate", response_model=SceneRead)
def regenerate_scene(
    video_id: uuid.UUID,
    scene_id: uuid.UUID,
    payload: SceneRegenerateRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Scene:
    """The "Regenerate" action on a storyboard scene (CLAUDE.md: Regenerate /
    Edit / Approve) — re-runs this one scene through the script engine. Same
    approval gate as the rest of the LLM-backed pipeline: if no provider is
    configured, this raises 402 with the cost warning instead of an empty
    500, so the frontend can show it the same way as any other blocked stage.
    """
    video = _owned_video_or_404(db, video_id, user)
    if video.storyboard_approved:
        raise HTTPException(
            status_code=409, detail="Storyboard already approved — scene is no longer editable"
        )

    script = db.query(Script).filter(Script.video_id == video_id).one_or_none()
    if script is None:
        raise HTTPException(status_code=404, detail="Script not generated yet")

    scene = db.get(Scene, scene_id)
    if scene is None or scene.script_id != script.id:
        raise HTTPException(status_code=404, detail="Scene not found on this video")

    draft = SceneDraft(
        order=scene.order,
        narration=scene.narration,
        visual_prompt=scene.visual_prompt,
        duration_seconds=scene.duration_seconds,
        transition=scene.transition.value,
    )

    instructions = payload.instructions if payload else ""
    try:
        regenerated = get_script_engine().regenerate_scene(video.topic, draft, instructions)
    except ApprovalRequiredError as exc:
        raise HTTPException(status_code=402, detail=exc.cost_warning.render()) from exc

    scene.narration = regenerated.narration
    scene.visual_prompt = regenerated.visual_prompt
    db.commit()
    db.refresh(scene)
    return scene


@router.get("/{video_id}/assets", response_model=list[AssetRead])
def list_assets(
    video_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[Asset]:
    _owned_video_or_404(db, video_id, user)
    return db.query(Asset).filter(Asset.video_id == video_id).order_by(Asset.created_at).all()


@router.post("/{video_id}/approve-storyboard", response_model=VideoRead)
def approve_storyboard(
    video_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Video:
    """Script → Storyboard → Approval → GPU generation. Nothing GPU-related
    starts before this call sets storyboard_approved=True."""
    video = _owned_video_or_404(db, video_id, user)
    if video.stage != PipelineStage.STORYBOARD_REVIEW:
        raise HTTPException(
            status_code=409,
            detail=f"Video is in stage '{video.stage.value}', not ready for storyboard approval",
        )

    video.storyboard_approved = True
    db.commit()
    db.refresh(video)

    enqueue_pipeline_start(video_id=video.id, run_research=False)

    return video


@router.post("/{video_id}/restart", response_model=VideoRead)
def restart_video(
    video_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Video:
    """Start production over from Topic. Deletes this video's generated work
    (research, script and scenes, compliance reports, voiceovers, clips,
    thumbnails, assets) and requeues it. Files already in storage are left
    alone; the new run writes new ones. Does not touch anything already
    published to YouTube."""
    video = _owned_video_or_404(db, video_id, user)

    video.script = None
    video.research = None
    video.voiceovers.clear()
    video.video_clips.clear()
    video.thumbnails.clear()
    video.assets.clear()
    db.query(ComplianceReport).filter(ComplianceReport.video_id == video.id).delete(
        synchronize_session=False
    )

    video.stage = PipelineStage.TOPIC
    video.stage_detail = ""
    video.stage_progress_percent = 0
    video.storyboard_approved = False
    video.final_video_path = None
    video.music_track = None
    video.auto_retry_count = 0
    db.commit()
    db.refresh(video)

    enqueue_pipeline_start(video_id=video.id, run_research=True)
    return video


_CRASHED_AT = re.compile(r"Crashed at '([a-z_]+)'")
_NOT_RESUMABLE = {PipelineStage.TOPIC, PipelineStage.COMPLETED, PipelineStage.FAILED}


@router.post("/{video_id}/continue", response_model=VideoRead)
def continue_video(
    video_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Video:
    """Resume a FAILED video at the stage that crashed. Everything already
    produced (research, script, approved storyboard, finished voiceovers and
    clips) is kept; the crashed stage and everything after it run again.
    Use Restart to start over from Topic instead."""
    video = _owned_video_or_404(db, video_id, user)
    if video.stage == PipelineStage.FAILED:
        # Resume at the stage named in the failure message.
        match = _CRASHED_AT.search(video.stage_detail or "")
        try:
            resume_stage = PipelineStage(match.group(1)) if match else None
        except ValueError:
            resume_stage = None
        if resume_stage is None or resume_stage in _NOT_RESUMABLE:
            raise HTTPException(
                status_code=409,
                detail="Can't tell which stage failed, so this can't be continued. Use Restart.",
            )
    else:
        # A video stuck mid-stage (its worker was replaced by a deploy, so the
        # job was lost without a failure being recorded) resumes where it is.
        # Storyboard review and the terminal stages aren't a stuck run.
        resume_stage = video.stage
        if resume_stage in _NOT_RESUMABLE or resume_stage == PipelineStage.STORYBOARD_REVIEW:
            raise HTTPException(
                status_code=409,
                detail="Only a failed or stuck video can be continued. Use Restart to start over.",
            )

    video.stage = resume_stage
    video.stage_detail = ""
    video.auto_retry_count = 0
    db.commit()
    db.refresh(video)

    enqueue_pipeline_start(video_id=video.id, run_research=False)
    return video


@router.post("/{video_id}/recover-clip", response_model=VideoRead)
def recover_clip(
    video_id: uuid.UUID,
    payload: ClipRecoverRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Video:
    """Attach a Runpod clip that was billed but never saved to the first scene
    still missing a clip, then resume video generation. The clip is polled,
    not submitted again, so this costs nothing new."""
    video = _owned_video_or_404(db, video_id, user)
    if video.stage == PipelineStage.FAILED:
        match = _CRASHED_AT.search(video.stage_detail or "")
        recoverable = bool(match) and match.group(1) == PipelineStage.VIDEO_GENERATION.value
    else:
        recoverable = video.stage == PipelineStage.VIDEO_GENERATION
    if not recoverable:
        raise HTTPException(
            status_code=409,
            detail="Recover applies to a video that failed or got stuck while generating clips.",
        )

    job_id = payload.runpod_job_id.strip()
    already = (
        db.query(VideoClip)
        .filter(VideoClip.video_id == video.id, VideoClip.provider_job_id == job_id)
        .first()
    )
    if already is not None:
        raise HTTPException(
            status_code=409, detail="That Runpod request is already attached to this video."
        )

    scenes = (
        db.query(Scene)
        .join(Script, Scene.script_id == Script.id)
        .filter(Script.video_id == video.id)
        .order_by(Scene.order)
        .all()
    )
    if not scenes:
        raise HTTPException(status_code=409, detail="This video has no scenes yet.")
    finished = {
        row.scene_id
        for row in db.query(VideoClip.scene_id).filter(
            VideoClip.video_id == video.id, VideoClip.status == JobStatus.SUCCEEDED
        )
    }
    target = next((scene for scene in scenes if scene.id not in finished), None)
    if target is None:
        raise HTTPException(
            status_code=409, detail="Every scene already has its clip, so nothing to recover."
        )

    db.add(
        VideoClip(
            video_id=video.id,
            scene_id=target.id,
            provider="recovered-runpod",
            status=JobStatus.QUEUED,
            provider_job_id=job_id,
        )
    )
    video.stage = PipelineStage.VIDEO_GENERATION
    video.stage_detail = ""
    db.commit()
    db.refresh(video)

    enqueue_pipeline_start(video_id=video.id, run_research=False)
    return video


@router.post("/{video_id}/youtube/upload", response_model=VideoRead)
def upload_to_youtube(
    video_id: uuid.UUID,
    payload: YouTubeUploadRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Video:
    """Always uploads private — see services/connectors/youtube/adapter.py.
    There is no parameter on this endpoint that can make it public."""
    video = _owned_video_or_404(db, video_id, user)
    if not video.final_video_path:
        raise HTTPException(status_code=409, detail="Video has no finished file to upload yet")

    youtube = YouTubeConnector(
        settings.google_youtube_client_id,
        settings.google_youtube_client_secret,
        settings.google_youtube_refresh_token,
    )
    try:
        result = youtube.upload_video(
            video.final_video_path, payload.title, payload.description, payload.tags
        )
    except EngineNotConfiguredError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    video.youtube_video_id = result.video_id
    db.commit()
    db.refresh(video)
    return video


@router.post("/{video_id}/youtube/publish", response_model=VideoRead)
def publish_to_youtube(
    video_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Video:
    """The one and only action that makes a video public. Never called
    automatically — only a direct request, here or via the assistant tool
    when Nobert explicitly asks for this exact video."""
    video = _owned_video_or_404(db, video_id, user)
    if not video.youtube_video_id:
        raise HTTPException(status_code=409, detail="Video hasn't been uploaded to YouTube yet")

    youtube = YouTubeConnector(
        settings.google_youtube_client_id,
        settings.google_youtube_client_secret,
        settings.google_youtube_refresh_token,
    )
    try:
        youtube.publish_video(video.youtube_video_id)
    except EngineNotConfiguredError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    video.youtube_published = True
    db.commit()
    db.refresh(video)
    return video


@router.post("/{video_id}/feedback", response_model=VideoFeedbackRead, status_code=201)
def add_video_feedback(
    video_id: uuid.UUID,
    payload: VideoFeedbackCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> VideoFeedback:
    """Nobert's note on a finished video — the real, honest version of
    "learning from mistakes": a growing history future script generation
    for this SAME PROJECT is given as context (see the SCRIPT stage in
    services/ai/orchestration/pipeline.py), not the model retraining
    itself."""
    video = _owned_video_or_404(db, video_id, user)

    feedback = VideoFeedback(project_id=video.project_id, video_id=video.id, note=payload.note)
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback
