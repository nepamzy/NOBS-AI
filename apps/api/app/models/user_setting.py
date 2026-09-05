import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class UserSetting(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Simple key/value settings table (default voice, default style, etc.).
    Table is named 'settings' per the CLAUDE.md schema list."""

    __tablename__ = "settings"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    key: Mapped[str] = mapped_column(String(100))
    value: Mapped[str] = mapped_column(String(2000), default="")

    user: Mapped["User"] = relationship(back_populates="settings")
