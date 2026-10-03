import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.video import Video


class VideoFeedback(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A short note Nobert leaves on a finished video — 'intro dragged',
    'great hook, more like this'. This is the real, honest version of
    "learning from its mistakes": not the model retraining itself, but a
    growing, visible history of his own notes that future script
    generation for the SAME PROJECT is explicitly given as context (see
    the SCRIPT stage in services/ai/orchestration/pipeline.py) — it
    changes future output because it's in the prompt, not because
    anything was fine-tuned."""

    __tablename__ = "video_feedback"

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"))
    video_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("videos.id"))
    note: Mapped[str] = mapped_column(Text)

    project: Mapped["Project"] = relationship()
    video: Mapped["Video"] = relationship()
