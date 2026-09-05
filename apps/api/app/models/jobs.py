import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import JobStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.video import Video


class GenerationJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A Video Job (Runpod -> Wan) or Voice Job (Chatterbox), tracked here so
    the API never blocks the browser on generation time (CLAUDE.md: Browser ->
    API -> Create Job -> Queue -> 'Processing...')."""

    __tablename__ = "generation_jobs"

    video_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("videos.id"))

    job_type: Mapped[str] = mapped_column(String(50))  # "video_clip" | "voiceover"
    scene_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scenes.id"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(100))
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="generation_job_status"), default=JobStatus.QUEUED
    )
    external_job_id: Mapped[str] = mapped_column(String(255), default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    video: Mapped["Video"] = relationship(back_populates="generation_jobs")


class RenderJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A Render Job: FFmpeg assembly of clips + voiceover + music + captions
    into the final MP4."""

    __tablename__ = "render_jobs"

    video_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("videos.id"))

    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="render_job_status"), default=JobStatus.QUEUED
    )
    progress_percent: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    video: Mapped["Video"] = relationship(back_populates="render_jobs")
