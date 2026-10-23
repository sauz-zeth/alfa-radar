"""add news impact metrics

Revision ID: b7d1e4f92a10
Revises: a0c5e5283689
Create Date: 2026-10-23 19:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b7d1e4f92a10"
down_revision: str | Sequence[str] | None = "a0c5e5283689"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "news_events",
        sa.Column(
            "impact_metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("news_events", "impact_metrics")
