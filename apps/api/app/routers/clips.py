import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.config import settings
from app.db import get_db
from app.jobs.queue import enqueue_clip_pipeline_start
from app.models.clip import Clip
from app.models.source_video import SourceVideo
from app.models.user import User
from app.schemas.clip import ClipRead, SourceVideoRead, SourceVideoUpdate
from services.common.errors import EngineNotConfiguredError
from services.connectors.youtube.adapter import YouTubeConnector

router = APIRouter(tags=["clips"])

_ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/x-matroska", "video/webm"}
_CHUNK_SIZE = 1024 * 1024  # 1MB — streamed to disk, never held fully in memory


def _owned_source_video_or_404(db: Session, source_video_id: uuid.UUID, user: User) -> SourceVideo:
    video = (
        db.query(SourceVideo)
        .filter(SourceVideo.id == source_video_id, SourceVideo.owner_id == user.id)
        .one_or_none()
    )
    if video is None:
        raise HTTPException(status_code=404, detail="Source video not found")
    return video


@router.post("/source-videos", response_model=SourceVideoRead, status_code=201)
async def upload_source_video(
    file: UploadFile, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> SourceVideo:
    if file.content_type not in _ALLOWED_VIDEO_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video type {file.content_type!r} — "
            "mp4, mov, mkv, and webm are supported.",
        )

    video_id = uuid.uuid4()
    dest_dir = Path(settings.local_storage_root) / "clips" / str(video_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "video.mp4").suffix or ".mp4"
    dest_path = dest_dir / f"source{suffix}"

    with open(dest_path, "wb") as out:
        while chunk := await file.read(_CHUNK_SIZE):
            out.write(chunk)

    source_video = SourceVideo(
        id=video_id,
        owner_id=user.id,
        original_filename=file.filename or "video.mp4",
        source_path=str(dest_path),
        target_clip_count=settings.clip_target_count,
    )
    db.add(source_video)
    db.commit()
    db.refresh(source_video)

    enqueue_clip_pipeline_start(source_video_id=source_video.id)

    return source_video


@router.get("/source-videos", response_model=list[SourceVideoRead])
def list_source_videos(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[SourceVideo]:
    return (
        db.query(SourceVideo)
        .filter(SourceVideo.owner_id == user.id)
        .order_by(SourceVideo.created_at.desc())
        .all()
    )


@router.get("/source-videos/{source_video_id}", response_model=SourceVideoRead)
def get_source_video(
    source_video_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SourceVideo:
    return _owned_source_video_or_404(db, source_video_id, user)


@router.patch("/source-videos/{source_video_id}", response_model=SourceVideoRead)
def update_source_video(
    source_video_id: uuid.UUID,
    payload: SourceVideoUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SourceVideo:
    source_video = _owned_source_video_or_404(db, source_video_id, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(source_video, field, value)
    db.commit()
    db.refresh(source_video)
    return source_video


@router.get("/source-videos/{source_video_id}/clips", response_model=list[ClipRead])
def list_clips(
    source_video_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Clip]:
    _owned_source_video_or_404(db, source_video_id, user)
    return (
        db.query(Clip)
        .filter(Clip.source_video_id == source_video_id)
        .order_by(Clip.start_seconds)
        .all()
    )


def _owned_clip_or_404(db: Session, clip_id: uuid.UUID, user: User) -> Clip:
    clip = (
        db.query(Clip)
        .join(SourceVideo, SourceVideo.id == Clip.source_video_id)
        .filter(Clip.id == clip_id, SourceVideo.owner_id == user.id)
        .one_or_none()
    )
    if clip is None:
        raise HTTPException(status_code=404, detail="Clip not found")
    return clip


@router.post("/clips/{clip_id}/publish", response_model=ClipRead)
def publish_clip(
    clip_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Clip:
    """Uploads (if not already) and publishes this clip to the SECOND
    YouTube channel. For use when SourceVideo.auto_publish was off — with
    it on, this already happened automatically once the clip was ready."""
    clip = _owned_clip_or_404(db, clip_id, user)
    if not clip.clip_path:
        raise HTTPException(status_code=409, detail="Clip hasn't finished rendering yet")

    youtube = YouTubeConnector(
        settings.clips_youtube_client_id,
        settings.clips_youtube_client_secret,
        settings.clips_youtube_refresh_token,
    )
    try:
        if not clip.youtube_video_id:
            result = youtube.upload_video(clip.clip_path, clip.title, clip.reason)
            clip.youtube_video_id = result.video_id
            db.commit()
        youtube.publish_video(clip.youtube_video_id)
    except EngineNotConfiguredError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc

    clip.youtube_published = True
    db.commit()
    db.refresh(clip)
    return clip
