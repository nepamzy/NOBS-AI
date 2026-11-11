"""add source/youtube_channel_title to waitlist_signups

The waitlist page now has three join paths — the plain email form, and
"Continue with Google"/"Continue with YouTube" (services/connectors/
google_waitlist_oauth) — so each signup records which one it came from,
plus the YouTube channel name when that variant's scope is granted.

Revision ID: e2f4a6b8c0d1
Revises: d1e3f5a7b9c2
"""

import sqlalchemy as sa
from alembic import op

revision = "e2f4a6b8c0d1"
down_revision = "d1e3f5a7b9c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "waitlist_signups",
        sa.Column("source", sa.String(length=20), nullable=False, server_default="form"),
    )
    op.add_column(
        "waitlist_signups",
        sa.Column("youtube_channel_title", sa.String(length=200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("waitlist_signups", "youtube_channel_title")
    op.drop_column("waitlist_signups", "source")
