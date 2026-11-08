"""add waitlist_signups

Captures email signups from the public landing page's "join the waitlist"
form (apps/landing) — no account, no auth, just a contact to notify once
NOBS AI opens up beyond the current private testing.

Revision ID: d1e3f5a7b9c2
Revises: c8d2e4f6a1b3
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d1e3f5a7b9c2"
down_revision = "c8d2e4f6a1b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "waitlist_signups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_waitlist_signups_email", "waitlist_signups", ["email"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_waitlist_signups_email", table_name="waitlist_signups")
    op.drop_table("waitlist_signups")
