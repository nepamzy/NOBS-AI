import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.jobs.queue import enqueue_pipeline_start
from app.models.enums import PipelineStage
from app.models.project import Project
from app.models.script import Script
from app.models.video import Video
from app.schemas.script import ScriptRead
from app.schemas.video import VideoCreate, VideoRead

router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("", response_model=VideoRead, status_code=201)
def create_video(payload: VideoCreate, db: Session = Depends(get_db)) -> Video:
    project = db.get(Project, payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    video = Video(
        project_id=project.id,
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


@router.get("/{video_id}", response_model=VideoRead)
def get_video(video_id: uuid.UUID, db: Session = Depends(get_db)) -> Video:
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.get("/{video_id}/script", response_model=ScriptRead)
def get_video_script(video_id: uuid.UUID, db: Session = Depends(get_db)) -> Script:
    script = db.query(Script).filter(Script.video_id == video_id).one_or_none()
    if script is None:
        raise HTTPException(status_code=404, detail="Script not generated yet")
    return script


@router.post("/{video_id}/approve-storyboard", response_model=VideoRead)
def approve_storyboard(video_id: uuid.UUID, db: Session = Depends(get_db)) -> Video:
    """Script → Storyboard → Approval → GPU generation. Nothing GPU-related
    starts before this call sets storyboard_approved=True."""
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
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
