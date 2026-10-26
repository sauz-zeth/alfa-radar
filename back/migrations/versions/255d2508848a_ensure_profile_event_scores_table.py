"""Add per-profile ML screening scores."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "255d2508848a"
down_revision: str | Sequence[str] | None = "new_ml_feed_runtime_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "profile_event_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="weak"),
        sa.Column("importance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("related", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("direct", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("fact", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("within_month", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("independent_source_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["profile_id"], ["business_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["news_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "event_id"),
    )
    for column in ("profile_id", "event_id", "status"):
        op.create_index(f"ix_profile_event_scores_{column}", "profile_event_scores", [column])


def downgrade() -> None:
    for column in ("profile_id", "event_id", "status"):
        op.drop_index(f"ix_profile_event_scores_{column}", table_name="profile_event_scores")
    op.drop_table("profile_event_scores")
