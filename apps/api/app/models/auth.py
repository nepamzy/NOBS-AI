import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class SignupPin(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A one-time, admin-issued invite code. Nobert generates one from the
    admin dashboard, sends it to exactly one person himself (outside the
    app), and it stops working the moment it's used once or 5 minutes pass
    — whichever comes first. code_hash, never the raw code, is stored;
    the plaintext is only ever returned once, at generation time."""

    __tablename__ = "signup_pins"

    code_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)


class AuthSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A logged-in session token. Deleting the row (logout, or an admin
    suspending/deleting the user) invalidates it immediately — no separate
    revocation list needed since every request re-checks the row exists."""

    __tablename__ = "auth_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship()
