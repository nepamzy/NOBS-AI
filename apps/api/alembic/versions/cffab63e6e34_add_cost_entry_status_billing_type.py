"""add status/billing_type to cost_entries, seed known real spend items

Revision ID: cffab63e6e34
Revises: 3965f368e0ab
Create Date: 2026-10-04 00:00:00.000000

Nobert asked for a real in-app spend dashboard instead of a separate
markdown file. These two columns turn the existing cost_entries table
(estimated/actual cost only) into something that can show "is this
still billing me right now" per service, and the seed rows below carry
over the known real-world items from this session's manual tracking
(Render, Redis Cloud, Supabase, Vercel, Runpod, Anthropic API,
Chatterbox) so the dashboard isn't empty on first load.
"""
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "cffab63e6e34"
down_revision: str | None = "3965f368e0ab"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # add_column doesn't auto-create enum types the way create_table does —
    # create them explicitly first, then reference with create_type=False.
    op.execute("CREATE TYPE cost_status AS ENUM ('ACTIVE', 'PENDING', 'STOPPED')")
    op.execute(
        "CREATE TYPE billing_type AS ENUM "
        "('HOURLY', 'PER_REQUEST', 'PER_TOKEN', 'MONTHLY', 'USAGE_BASED', 'ONE_TIME', 'FREE')"
    )

    op.add_column(
        "cost_entries",
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "PENDING", "STOPPED", name="cost_status", create_type=False),
            nullable=False,
            server_default="ACTIVE",
        ),
    )
    op.add_column(
        "cost_entries",
        sa.Column(
            "billing_type",
            sa.Enum(
                "HOURLY",
                "PER_REQUEST",
                "PER_TOKEN",
                "MONTHLY",
                "USAGE_BASED",
                "ONE_TIME",
                "FREE",
                name="billing_type",
                create_type=False,
            ),
            nullable=True,
        ),
    )

    cost_entries = sa.table(
        "cost_entries",
        sa.column("id", sa.UUID()),
        sa.column(
            "category",
            sa.Enum(
                "GPU",
                "LLM",
                "TTS",
                "VIDEO_GENERATION",
                "STORAGE",
                "DATABASE",
                "HOSTING",
                "NETWORKING",
                "DOMAIN",
                "OTHER",
                name="cost_category",
                create_type=False,
            ),
        ),
        sa.column("service", sa.String()),
        sa.column("purpose", sa.Text()),
        sa.column(
            "status",
            sa.Enum("ACTIVE", "PENDING", "STOPPED", name="cost_status", create_type=False),
        ),
        sa.column(
            "billing_type",
            sa.Enum(
                "HOURLY",
                "PER_REQUEST",
                "PER_TOKEN",
                "MONTHLY",
                "USAGE_BASED",
                "ONE_TIME",
                "FREE",
                name="billing_type",
                create_type=False,
            ),
        ),
        sa.column("estimated_cost_usd", sa.Float()),
        sa.column("actual_cost_usd", sa.Float()),
    )

    op.bulk_insert(
        cost_entries,
        [
            {
                "id": uuid.uuid4(),
                "category": "HOSTING",
                "service": "Render — Web Service (nobs-ai-api)",
                "purpose": "Free tier; sleeps after ~15min idle.",
                "status": "ACTIVE",
                "billing_type": "MONTHLY",
                "estimated_cost_usd": 0.0,
                "actual_cost_usd": 0.0,
            },
            {
                "id": uuid.uuid4(),
                "category": "HOSTING",
                "service": "Render — Background Worker",
                "purpose": "Runs pipeline jobs. Price estimated — not yet confirmed against a real Render invoice.",
                "status": "ACTIVE",
                "billing_type": "MONTHLY",
                "estimated_cost_usd": 7.0,
                "actual_cost_usd": None,
            },
            {
                "id": uuid.uuid4(),
                "category": "HOSTING",
                "service": "Redis Cloud",
                "purpose": "Free tier (30MB) job queue + rate limiting. Replaced Render's paid Redis add-on.",
                "status": "ACTIVE",
                "billing_type": "MONTHLY",
                "estimated_cost_usd": 0.0,
                "actual_cost_usd": 0.0,
            },
            {
                "id": uuid.uuid4(),
                "category": "HOSTING",
                "service": "Render — paid Redis (nobs-ai-redis)",
                "purpose": "Pre-existing paid Redis instance, running unnoticed since Sep 7. Deleted per Nobert's instruction after discovery.",
                "status": "STOPPED",
                "billing_type": "MONTHLY",
                "estimated_cost_usd": 10.0,
                "actual_cost_usd": None,
            },
            {
                "id": uuid.uuid4(),
                "category": "DATABASE",
                "service": "Supabase",
                "purpose": "Postgres + file storage, free tier.",
                "status": "ACTIVE",
                "billing_type": "MONTHLY",
                "estimated_cost_usd": 0.0,
                "actual_cost_usd": 0.0,
            },
            {
                "id": uuid.uuid4(),
                "category": "HOSTING",
                "service": "Vercel",
                "purpose": "Frontend hosting, free (Hobby) tier.",
                "status": "ACTIVE",
                "billing_type": "MONTHLY",
                "estimated_cost_usd": 0.0,
                "actual_cost_usd": 0.0,
            },
            {
                "id": uuid.uuid4(),
                "category": "GPU",
                "service": "Runpod (RTX 4090 pod)",
                "purpose": "For Chatterbox/Wan hosting. $10 minimum account credit required to deploy; GPU billed $0.74/hr while running, plus volume-disk storage while it exists. Not yet confirmed deployed.",
                "status": "PENDING",
                "billing_type": "HOURLY",
                "estimated_cost_usd": None,
                "actual_cost_usd": None,
            },
            {
                "id": uuid.uuid4(),
                "category": "LLM",
                "service": "Anthropic API",
                "purpose": "Script/research/assistant chat calls. Key is live; no real video generated end-to-end yet.",
                "status": "ACTIVE",
                "billing_type": "PER_TOKEN",
                "estimated_cost_usd": None,
                "actual_cost_usd": None,
            },
            {
                "id": uuid.uuid4(),
                "category": "TTS",
                "service": "Chatterbox (self-hosted software)",
                "purpose": "Open-source (MIT), no license/per-call fee. Only real cost is whichever hardware runs it — see the GPU row above, or $0 on Nobert's own PC.",
                "status": "PENDING",
                "billing_type": "FREE",
                "estimated_cost_usd": 0.0,
                "actual_cost_usd": 0.0,
            },
        ],
    )


def downgrade() -> None:
    op.drop_column("cost_entries", "billing_type")
    op.drop_column("cost_entries", "status")
    op.execute("DROP TYPE IF EXISTS billing_type")
    op.execute("DROP TYPE IF EXISTS cost_status")
