import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db import get_db
from app.engines import get_script_engine
from app.jobs.queue import enqueue_pipeline_start
from app.models.asset import Asset
from app.models.enums import PipelineStage, UserRole
from app.models.project import Project
from app.models.script import Scene, Script
from app.models.user import User
from app.models.video import Video
from app.schemas.asset import AssetRead
from app.schemas.script import SceneRead, SceneUpdate, ScriptRead
from app.schemas.video import VideoCreate, VideoRead
from services.ai.script.engine import SceneDraft
from services.common.errors import ApprovalRequiredError

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

    try:
        regenerated = get_script_engine().regenerate_scene(video.topic, draft)
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
