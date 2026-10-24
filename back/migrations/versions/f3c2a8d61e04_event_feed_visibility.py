"""add event feed visibility

Revision ID: f3c2a8d61e04
Revises: e5a1c9d2f3b7
Create Date: 2026-10-24 14:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f3c2a8d61e04"
down_revision: str | Sequence[str] | None = "e5a1c9d2f3b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "news_events",
        sa.Column("is_feed_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index(
        "ix_news_events_is_feed_visible", "news_events", ["is_feed_visible"]
    )


def downgrade() -> None:
    op.drop_index("ix_news_events_is_feed_visible", table_name="news_events")
    op.drop_column("news_events", "is_feed_visible")
