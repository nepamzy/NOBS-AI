"""add video producer, awaiting_claude stage and scheduled publish

Revision ID: a7c1d3e5f902
Revises: f9bc9f6ecc77
Create Date: 2026-11-15 10:30:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = 'a7c1d3e5f902'
down_revision: str | None = 'f9bc9f6ecc77'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The enum value MUST be added here — the code uses it as soon as it
    # deploys (see f0f0e2eaa26c for what happens when a migration is missed).
    op.execute(
        "ALTER TYPE pipeline_stage ADD VALUE IF NOT EXISTS 'AWAITING_CLAUDE' "
        "AFTER 'COMPLIANCE_CHECK'"
    )
    op.add_column(
        'videos',
        sa.Column('producer', sa.String(length=20), server_default='runpod', nullable=False),
    )
    op.add_column(
        'videos', sa.Column('scheduled_publish_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column('videos', sa.Column('youtube_title', sa.String(length=500), nullable=True))
    op.add_column('videos', sa.Column('youtube_description', sa.Text(), nullable=True))
    op.add_column('videos', sa.Column('publish_error', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('videos', 'publish_error')
    op.drop_column('videos', 'youtube_description')
    op.drop_column('videos', 'youtube_title')
    op.drop_column('videos', 'scheduled_publish_at')
    op.drop_column('videos', 'producer')
    # Postgres can't drop an enum value; 'AWAITING_CLAUDE' stays in the type.
