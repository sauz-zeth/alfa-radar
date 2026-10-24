"""add event analyses

Revision ID: a7d2e9c14b83
Revises: f3c2a8d61e04
Create Date: 2026-10-24 15:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a7d2e9c14b83"
down_revision: str | Sequence[str] | None = "f3c2a8d61e04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["event_id"], ["news_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["business_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "event_id"),
    )
    op.create_index("ix_event_analyses_event_id", "event_analyses", ["event_id"])
    op.create_index("ix_event_analyses_profile_id", "event_analyses", ["profile_id"])


def downgrade() -> None:
    op.drop_index("ix_event_analyses_profile_id", table_name="event_analyses")
    op.drop_index("ix_event_analyses_event_id", table_name="event_analyses")
    op.drop_table("event_analyses")
