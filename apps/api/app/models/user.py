from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import UserRole
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user_setting import UserSetting


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """ADMIN is Nobert (exactly one, bootstrapped from ADMIN_EMAIL/
    ADMIN_PASSWORD on first startup — see app/bootstrap.py). USER accounts
    are created only via a valid, unused, unexpired SignupPin an admin
    issued. token_balance is a placeholder unit standing in for real
    payment (not built yet) — 1 token = 1 video creation for non-admin
    users; ADMIN is exempt from the check entirely."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True)
    display_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), default=UserRole.USER)
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    token_balance: Mapped[int] = mapped_column(Integer, default=0)

    # delete-orphan: deleting a guest's account takes their private
    # projects/videos/settings with it (per the "fully separate, private
    # data" design — the admin manages accounts, not their content).
    projects: Mapped[list["Project"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    settings: Mapped[list["UserSetting"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
