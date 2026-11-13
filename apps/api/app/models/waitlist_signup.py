from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class WaitlistSignup(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One email from the public landing page's "join the waitlist" form
    (apps/web/src/landing) — not a user account, no auth, no token_balance. Just a
    contact to email once NOBS AI opens up beyond the current private
    testing (CLAUDE.md Part 2 — V1 is single-user; this is how interest
    from outside people gets captured for V2+ without building real
    multi-tenant signup yet)."""

    __tablename__ = "waitlist_signups"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    # "form" (plain email form), "google_oauth", or "youtube_oauth" — which
    # of the waitlist page's three join paths this came from (see
    # app/routers/waitlist_oauth.py). Informational only, nothing reads it
    # to change behavior.
    source: Mapped[str] = mapped_column(String(20), default="form")
    youtube_channel_title: Mapped[str | None] = mapped_column(String(200), default=None)
