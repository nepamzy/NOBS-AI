import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class ConnectorKey(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A secret that lets an outside Claude session (via the NOBS AI MCP
    connector, apps/api/app/routers/connector.py) hand finished videos to
    one specific NOBS AI account. Only a peppered hash is stored — the
    plaintext is shown once, at creation. Revoking flips `revoked`, which
    takes effect on the very next request (the key is looked up every time).

    A key can only IMPORT and READ: there is deliberately no tool or
    endpoint behind it that publishes to YouTube or deletes anything."""

    __tablename__ = "connector_keys"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(100))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    # First few characters of the key, so the list view can tell keys apart
    # without ever exposing a usable secret.
    key_prefix: Mapped[str] = mapped_column(String(16))
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship()
