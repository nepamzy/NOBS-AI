"""count clip-pipeline attempts so an interrupted upload can be retried safely

Revision ID: d1f4a6b8c235
Revises: c9e3f5a7b124
Create Date: 2026-11-16 09:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = 'd1f4a6b8c235'
down_revision: str | None = 'c9e3f5a7b124'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'source_videos',
        sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
    )


def downgrade() -> None:
    op.drop_column('source_videos', 'attempts')
