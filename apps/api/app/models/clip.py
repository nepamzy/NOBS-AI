import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.source_video import SourceVideo


class Clip(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One short clip selected and cut from a SourceVideo."""

    __tablename__ = "clips"

    source_video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_videos.id")
    )

    start_seconds: Mapped[float] = mapped_column(Float)
    end_seconds: Mapped[float] = mapped_column(Float)
    title: Mapped[str] = mapped_column(String(200))
    # The LLM's own short explanation of why this moment was picked — shown
    # in the UI so Nobert can sanity-check the selection, not just the cut.
    reason: Mapped[str] = mapped_column(Text, default="")

    clip_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    youtube_video_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    youtube_published: Mapped[bool] = mapped_column(Boolean, default=False)

    source_video: Mapped["SourceVideo"] = relationship(back_populates="clips")
