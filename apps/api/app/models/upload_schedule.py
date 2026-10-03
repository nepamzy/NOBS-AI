import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.project import Project


class UploadSchedule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A recurring weekly slot: 'every Monday at 16:00 UTC, start a
    5-minute video about X'. The scheduler only ever creates the Video and
    enqueues the normal pipeline (services/ai/orchestration/pipeline.py) —
    it STOPS at the existing STORYBOARD_REVIEW gate exactly like a manually
    created video, so a schedule never generates or spends anything without
    Nobert's review. There is no "auto-publish" concept here at all; that
    lives, deliberately absent, in services/connectors/youtube/adapter.py."""

    __tablename__ = "upload_schedules"

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"))

    # 0=Monday .. 6=Sunday (Python's datetime.weekday() convention).
    day_of_week: Mapped[int] = mapped_column(Integer)
    # "HH:MM" 24-hour, UTC. This is when the video is STARTED, not published
    # — leave enough lead time before you'd want it live for yourself to
    # review the storyboard and, once generated, watch the result.
    trigger_time: Mapped[str] = mapped_column(String(5))

    topic: Mapped[str] = mapped_column(Text)
    target_duration_seconds: Mapped[int] = mapped_column(Integer)
    voice_preset: Mapped[str] = mapped_column(String(100), default="")
    style_preset: Mapped[str] = mapped_column(String(100), default="")
    run_research: Mapped[bool] = mapped_column(Boolean, default=True)

    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # Guards against firing twice for the same slot if the due-check runs
    # more than once within the same minute (e.g. worker restart).
    last_triggered_on: Mapped[str | None] = mapped_column(String(10), nullable=True)

    project: Mapped["Project"] = relationship()
