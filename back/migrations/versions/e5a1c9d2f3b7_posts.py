"""add posts for news pipeline

Revision ID: e5a1c9d2f3b7
Revises: c1f7a2d94b30
Create Date: 2026-10-24 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e5a1c9d2f3b7"
down_revision: str | Sequence[str] | None = "c1f7a2d94b30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_name", sa.String(length=128), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "raw",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "parsed",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "categories",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "embedding",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("cluster_key", sa.String(length=64), nullable=True),
        sa.Column("news_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tracked_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("importance", sa.Integer(), nullable=True),
        sa.Column("similarity", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="received"),
        sa.Column("stage", sa.String(length=32), nullable=False, server_default="received"),
        sa.Column(
            "decision_trace",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["news_event_id"],
            ["news_events.id"],
            name=op.f("fk_posts_news_event_id_news_events"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tracked_item_id"],
            ["tracked_items.id"],
            name=op.f("fk_posts_tracked_item_id_tracked_items"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_posts")),
    )
    op.create_index(op.f("ix_posts_cluster_key"), "posts", ["cluster_key"], unique=False)
    op.create_index(op.f("ix_posts_published_at"), "posts", ["published_at"], unique=False)
    op.create_index(op.f("ix_posts_news_event_id"), "posts", ["news_event_id"], unique=False)
    op.create_index(op.f("ix_posts_status"), "posts", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_posts_status"), table_name="posts")
    op.drop_index(op.f("ix_posts_news_event_id"), table_name="posts")
    op.drop_index(op.f("ix_posts_published_at"), table_name="posts")
    op.drop_index(op.f("ix_posts_cluster_key"), table_name="posts")
    op.drop_table("posts")
