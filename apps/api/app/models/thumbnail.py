import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.video import Video


class Thumbnail(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One of several A/B/C thumbnail options generated after the video
    completes, plus which one (if any) the user picked."""

    __tablename__ = "thumbnails"

    video_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("videos.id"))

    image_path: Mapped[str] = mapped_column(String(1000))
    variant_label: Mapped[str] = mapped_column(String(10), default="A")
    selected: Mapped[bool] = mapped_column(default=False)

    video: Mapped["Video"] = relationship(back_populates="thumbnails")
