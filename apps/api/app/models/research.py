import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.video import Video


class Research(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Structured research output (CLAUDE.md Part 3): key facts, statistics,
    interesting findings, counterarguments, story opportunities — not a blob."""

    __tablename__ = "research"

    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("videos.id"), unique=True
    )

    topic: Mapped[str] = mapped_column(Text)
    key_facts: Mapped[list] = mapped_column(JSONB, default=list)
    statistics: Mapped[list] = mapped_column(JSONB, default=list)
    interesting_findings: Mapped[list] = mapped_column(JSONB, default=list)
    counterarguments: Mapped[list] = mapped_column(JSONB, default=list)
    story_opportunities: Mapped[list] = mapped_column(JSONB, default=list)

    video: Mapped["Video"] = relationship(back_populates="research")
    sources: Mapped[list["ResearchSource"]] = relationship(
        back_populates="research", cascade="all, delete-orphan"
    )


class ResearchSource(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "research_sources"

    research_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("research.id"))

    url: Mapped[str] = mapped_column(String(2000))
    title: Mapped[str] = mapped_column(String(500), default="")
    excerpt: Mapped[str] = mapped_column(Text, default="")

    research: Mapped["Research"] = relationship(back_populates="sources")
