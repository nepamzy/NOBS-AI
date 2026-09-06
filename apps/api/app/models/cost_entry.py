import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import CostCategory
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class CostEntry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Spend tracking per CLAUDE.md Part 4: Estimated cost, Actual cost,
    Purpose, Date, Service, Project/video, Category. Nothing in this
    codebase writes here automatically yet — no paid adapter actually
    calls anything (see services/*/adapter.py) — so this stays empty until
    a real paid action runs, or Nobert logs one manually."""

    __tablename__ = "cost_entries"

    category: Mapped[CostCategory] = mapped_column(Enum(CostCategory, name="cost_category"))
    service: Mapped[str] = mapped_column(String(255))
    purpose: Mapped[str] = mapped_column(Text)
    video_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("videos.id"), nullable=True
    )

    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
