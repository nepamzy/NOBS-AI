import uuid

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AssistantMemory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One growing notes blob per user, read into the assistant's system
    prompt on every turn and appended to via the `remember` tool. This is
    NOT the model getting smarter — it's the same model every time, just
    given a written note of what it's been told before, the same way a
    person would use a notebook."""

    __tablename__ = "assistant_memory"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True
    )
    content: Mapped[str] = mapped_column(Text, default="")
