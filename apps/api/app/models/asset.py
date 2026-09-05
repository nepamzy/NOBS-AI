import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import AssetType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.video import Video


class Asset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Unified index of every file a project produces, so the Project page's
    'Assets' list (Script, Voiceover, each Scene, Thumbnail, Captions, Final
    Video) is one query instead of joining five tables."""

    __tablename__ = "assets"

    video_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("videos.id"))

    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType, name="asset_type"))
    path: Mapped[str] = mapped_column(String(1000))
    label: Mapped[str] = mapped_column(String(255), default="")

    video: Mapped["Video"] = relationship(back_populates="assets")
