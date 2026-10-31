"""add auto_retry_count to videos

Lets services/scheduling/auto_retry.py cap how many times it automatically
resumes a crashed video before leaving it for a human — without this, a
persistently-broken video could get auto-retried forever.

Revision ID: c8d2e4f6a1b3
Revises: b7c1d2e3f4a5
"""

import sqlalchemy as sa
from alembic import op

revision = "c8d2e4f6a1b3"
down_revision = "b7c1d2e3f4a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "videos",
        sa.Column("auto_retry_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("videos", "auto_retry_count")
