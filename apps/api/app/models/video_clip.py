import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import JobStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.script import Scene
    from app.models.video import Video


class VideoClip(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One generated clip per scene (5-12s). Regenerating a bad scene means
    replacing one row here, not re-running the whole video (CLAUDE.md Part 3)."""

    __tablename__ = "video_clips"

    video_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("videos.id"))
    scene_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scenes.id"))

    provider: Mapped[str] = mapped_column(String(100))
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="clip_job_status"), default=JobStatus.QUEUED
    )
    clip_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    video: Mapped["Video"] = relationship(back_populates="video_clips")
    scene: Mapped["Scene"] = relationship(back_populates="video_clips")
