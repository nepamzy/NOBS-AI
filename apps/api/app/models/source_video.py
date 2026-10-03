import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import ClipJobStage
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.clip import Clip
    from app.models.user import User


class SourceVideo(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An already-finished video Nobert uploads to be clipped — separate
    from the Project/Video tree (those are for videos NOBS AI generates
    from a topic; this is the opposite direction: an existing video goes
    IN, short clips come out). Owned directly by a user, no project."""

    __tablename__ = "source_videos"

    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    original_filename: Mapped[str] = mapped_column(String(500))
    source_path: Mapped[str] = mapped_column(String(1000))

    stage: Mapped[ClipJobStage] = mapped_column(
        Enum(ClipJobStage, name="clip_job_stage"), default=ClipJobStage.UPLOADED
    )
    stage_detail: Mapped[str] = mapped_column(Text, default="")
    target_clip_count: Mapped[int] = mapped_column(Integer, default=5)
    # Written once transcription finishes so a later stage (or a retry
    # after a blocked clip-selection step) never has to re-transcribe.
    transcript_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # Defaults True — Nobert's explicit instruction for this feature ("give
    # it a video, it ships to the other channel"), unlike every other
    # auto-publish flag in this app (UploadSchedule.auto_publish), which
    # defaults False. He can still turn it off per upload.
    auto_publish: Mapped[bool] = mapped_column(Boolean, default=True)

    owner: Mapped["User"] = relationship()
    clips: Mapped[list["Clip"]] = relationship(
        back_populates="source_video", cascade="all, delete-orphan"
    )
