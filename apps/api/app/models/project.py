import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.video import Video


class Project(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A project groups one or more Video attempts under a single topic/name."""

    __tablename__ = "projects"

    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255))

    owner: Mapped["User"] = relationship(back_populates="projects")
    videos: Mapped[list["Video"]] = relationship(back_populates="project")
