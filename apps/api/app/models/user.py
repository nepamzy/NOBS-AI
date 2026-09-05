from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user_setting import UserSetting


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """V1 is single-user (Nobert only) but the table exists so auth/multi-user
    is a later addition, not a schema rewrite."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True)
    display_name: Mapped[str] = mapped_column(String(255))

    projects: Mapped[list["Project"]] = relationship(back_populates="owner")
    settings: Mapped[list["UserSetting"]] = relationship(back_populates="user")
