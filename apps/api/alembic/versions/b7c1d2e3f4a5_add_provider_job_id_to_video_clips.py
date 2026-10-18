"""add provider_job_id to video_clips

Stores the Runpod job id as soon as a clip is submitted, so a job that is
lost (worker replaced mid-run) can be picked up again instead of billed twice.

Revision ID: b7c1d2e3f4a5
Revises: cffab63e6e34
"""

import sqlalchemy as sa
from alembic import op

revision = "b7c1d2e3f4a5"
down_revision = "cffab63e6e34"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("video_clips", sa.Column("provider_job_id", sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column("video_clips", "provider_job_id")
