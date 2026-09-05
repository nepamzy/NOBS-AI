import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import TransitionType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.video import Video
    from app.models.video_clip import VideoClip


class Script(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Structured scenes, not a flat text blob (CLAUDE.md Part 3 — this is what
    makes the video-generation stage tractable)."""

    __tablename__ = "scripts"

    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("videos.id"), unique=True
    )

    title: Mapped[str] = mapped_column(String(500))
    hook: Mapped[str] = mapped_column(Text)
    estimated_duration_seconds: Mapped[int] = mapped_column(Integer)
    word_count: Mapped[int] = mapped_column(Integer)
    approved: Mapped[bool] = mapped_column(default=False)

    video: Mapped["Video"] = relationship(back_populates="script")
    scenes: Mapped[list["Scene"]] = relationship(
        back_populates="script", order_by="Scene.order", cascade="all, delete-orphan"
    )


class Scene(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One scene: narration, visual_prompt, duration, transition. A 3-minute
    video is ~15-25 of these, each rendered as its own 5-12s clip."""

    __tablename__ = "scenes"

    script_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scripts.id"))

    order: Mapped[int] = mapped_column(Integer)
    narration: Mapped[str] = mapped_column(Text)
    visual_prompt: Mapped[str] = mapped_column(Text)
    duration_seconds: Mapped[int] = mapped_column(Integer)
    transition: Mapped[TransitionType] = mapped_column(
        Enum(TransitionType, name="transition_type"), default=TransitionType.CUT
    )

    script: Mapped["Script"] = relationship(back_populates="scenes")
    video_clips: Mapped[list["VideoClip"]] = relationship(back_populates="scene")
