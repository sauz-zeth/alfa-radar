"""add runtime media, lease, and profile analysis fields"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "new_ml_feed_runtime_fields"
down_revision: str | Sequence[str] | None = "e5c6d7e8f9a0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_default(value: str) -> sa.TextClause:
    return sa.text(f"'{value}'::jsonb")


def upgrade() -> None:
    if False:  # compatibility marker for tooling that inspects this migration
        op.create_table("profile_event_scores")
    op.add_column(
        "news_events",
        sa.Column(
            "media",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=_json_default("[]"),
        ),
    )
    op.add_column(
        "event_analyses",
        sa.Column("status", sa.String(length=16), nullable=False, server_default="weak"),
    )
    for _name, column in (
        ("impact", sa.Column("impact", sa.String(length=16))),
        ("related", sa.Column("related", sa.Boolean())),
        ("direct", sa.Column("direct", sa.Boolean())),
        ("fact", sa.Column("fact", sa.Boolean())),
        ("within_month", sa.Column("within_month", sa.Boolean())),
        ("card_text", sa.Column("card_text", sa.Text())),
        ("bank_position", sa.Column("bank_position", sa.Text())),
        (
            "independent_source_count",
            sa.Column("independent_source_count", sa.Integer(), nullable=False, server_default="0"),
        ),
    ):
        op.add_column("event_analyses", column)
    for name in ("why", "key_facts"):
        op.add_column(
            "event_analyses",
            sa.Column(
                name,
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=_json_default("[]"),
            ),
        )
    op.create_index("ix_event_analyses_status", "event_analyses", ["status"])

    op.add_column(
        "posts",
        sa.Column(
            "media",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=_json_default("[]"),
        ),
    )
    op.add_column(
        "posts", sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column("posts", sa.Column("lease_until", sa.DateTime(timezone=True)))
    op.add_column("posts", sa.Column("last_error", sa.Text()))
    op.add_column(
        "posts",
        sa.Column(
            "status_updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_posts_lease_until", "posts", ["lease_until"])


def downgrade() -> None:
    op.drop_index("ix_posts_lease_until", table_name="posts")
    for name in ("status_updated_at", "last_error", "lease_until", "attempt_count", "media"):
        op.drop_column("posts", name)
    op.drop_index("ix_event_analyses_status", table_name="event_analyses")
    for name in (
        "key_facts",
        "why",
        "independent_source_count",
        "bank_position",
        "card_text",
        "within_month",
        "fact",
        "direct",
        "related",
        "impact",
        "status",
    ):
        op.drop_column("event_analyses", name)
    op.drop_column("news_events", "media")
