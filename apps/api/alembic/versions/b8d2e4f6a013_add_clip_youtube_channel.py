"""record which YouTube channel a clip was uploaded to

Revision ID: b8d2e4f6a013
Revises: a7c1d3e5f902
Create Date: 2026-11-15 12:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = 'b8d2e4f6a013'
down_revision: str | None = 'a7c1d3e5f902'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('clips', sa.Column('youtube_channel', sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column('clips', 'youtube_channel')
