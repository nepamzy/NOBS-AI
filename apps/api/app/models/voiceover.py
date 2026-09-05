import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.video import Video


class Voiceover(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Output of the Voice Engine (Chatterbox today, swappable later).
    word_timestamps feeds the captions pipeline (Voice → ASR → timestamps →
    subtitles → FFmpeg, per CLAUDE.md)."""

    __tablename__ = "voiceovers"

    video_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("videos.id"))

    provider: Mapped[str] = mapped_column(String(100))
    audio_path: Mapped[str] = mapped_column(String(1000))
    duration_seconds: Mapped[float] = mapped_column(Float)
    word_timestamps: Mapped[list] = mapped_column(JSONB, default=list)

    video: Mapped["Video"] = relationship(back_populates="voiceovers")
