import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.video import Video


class ComplianceReport(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Result of the heuristic policy-risk scan every video's script goes
    through before any voice/video generation runs (services/compliance).
    This is a best-effort keyword/pattern scanner, NOT a guarantee of
    YouTube compliance — only YouTube's own systems make that call. blockers
    stop the pipeline; warnings don't, but are worth reading."""

    __tablename__ = "compliance_reports"

    video_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("videos.id"))
    passed: Mapped[bool] = mapped_column(Boolean)
    blockers: Mapped[list] = mapped_column(JSONB, default=list)
    warnings: Mapped[list] = mapped_column(JSONB, default=list)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    video: Mapped["Video"] = relationship()
