"""Store Kimi business theses with profile scores."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "add_profile_score_why"
down_revision = "255d2508848a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "profile_event_scores",
        sa.Column(
            "why",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("profile_event_scores", "why")
