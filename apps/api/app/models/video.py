import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import PipelineStage
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.jobs import GenerationJob, RenderJob
    from app.models.project import Project
    from app.models.research import Research
    from app.models.script import Script
    from app.models.thumbnail import Thumbnail
    from app.models.video_clip import VideoClip
    from app.models.voiceover import Voiceover


class Video(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One video attempt: Topic → ... → Final MP4. Holds pipeline status so the
    frontend can show 'Generating video... 72% — Scene 8 of 11' without polling
    every child table."""

    __tablename__ = "videos"

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"))

    topic: Mapped[str] = mapped_column(Text)
    target_duration_seconds: Mapped[int] = mapped_column(Integer)
    voice_preset: Mapped[str] = mapped_column(String(100), default="")
    style_preset: Mapped[str] = mapped_column(String(100), default="")

    stage: Mapped[PipelineStage] = mapped_column(
        Enum(PipelineStage, name="pipeline_stage"), default=PipelineStage.TOPIC
    )
    stage_progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    # Text, not String(255): this holds full cost-warning / blocked-reason
    # messages (CLAUDE.md Part 1's cost warning block), which run well past 255 chars.
    stage_detail: Mapped[str] = mapped_column(Text, default="")

    storyboard_approved: Mapped[bool] = mapped_column(default=False)

    final_video_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="videos")
    script: Mapped["Script | None"] = relationship(
        back_populates="video", uselist=False, cascade="all, delete-orphan"
    )
    research: Mapped["Research | None"] = relationship(
        back_populates="video", uselist=False, cascade="all, delete-orphan"
    )
    voiceovers: Mapped[list["Voiceover"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    video_clips: Mapped[list["VideoClip"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    thumbnails: Mapped[list["Thumbnail"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    assets: Mapped[list["Asset"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    generation_jobs: Mapped[list["GenerationJob"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    render_jobs: Mapped[list["RenderJob"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
