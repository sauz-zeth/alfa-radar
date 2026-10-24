"""add event questions

Revision ID: c1f7a2d94b30
Revises: b7d1e4f92a10
Create Date: 2026-10-24 12:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c1f7a2d94b30"
down_revision: str | Sequence[str] | None = "b7d1e4f92a10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="waiting"),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=128), nullable=True),
        sa.Column("date", sa.String(length=16), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["profile_id"], ["business_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["news_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_event_questions_profile_id", "event_questions", ["profile_id"])
    op.create_index("ix_event_questions_event_id", "event_questions", ["event_id"])
    op.create_index(
        "ix_event_questions_profile_event", "event_questions", ["profile_id", "event_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_event_questions_profile_event", table_name="event_questions")
    op.drop_index("ix_event_questions_event_id", table_name="event_questions")
    op.drop_index("ix_event_questions_profile_id", table_name="event_questions")
    op.drop_table("event_questions")
