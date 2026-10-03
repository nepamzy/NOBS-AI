"""add compliance check to pipeline stage enum

The 'compliance_check' stage has existed in app/models/enums.py and been
used by services/ai/orchestration/pipeline.py since that stage was added,
but no migration ever added the value to the Postgres enum — the initial
schema migration (d1050c39cff2) only created
TOPIC/RESEARCH/SCRIPT/STORYBOARD_REVIEW/VOICE/VIDEO_GENERATION/ASSEMBLY/
CAPTIONS/THUMBNAIL/COMPLETED/FAILED. Any real video would have crashed
the instant it reached COMPLIANCE_CHECK with
"invalid input value for enum pipeline_stage". Caught by hand-testing the
pipeline locally, not by anything that touched this stage before.

Revision ID: f0f0e2eaa26c
Revises: eb99ad62e1a7
Create Date: 2026-10-03 14:20:19.005960

"""
from collections.abc import Sequence

from alembic import op

revision: str = 'f0f0e2eaa26c'
down_revision: str | None = 'eb99ad62e1a7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE pipeline_stage ADD VALUE IF NOT EXISTS 'COMPLIANCE_CHECK' "
        "AFTER 'STORYBOARD_REVIEW'"
    )


def downgrade() -> None:
    # Postgres has no DROP VALUE for enums — removing one requires rebuilding
    # the type (create new type, migrate the column, drop the old type).
    # Not implemented: no code path in this app ever needs to downgrade past
    # this, and a video genuinely sitting at COMPLIANCE_CHECK would have
    # nowhere valid to go if the value vanished under it.
    pass
