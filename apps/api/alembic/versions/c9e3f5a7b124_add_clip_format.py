"""record whether a Claude-supplied clip is a short or a long video

Revision ID: c9e3f5a7b124
Revises: b8d2e4f6a013
Create Date: 2026-11-15 21:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = 'c9e3f5a7b124'
down_revision: str | None = 'b8d2e4f6a013'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('clips', sa.Column('format', sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column('clips', 'format')
