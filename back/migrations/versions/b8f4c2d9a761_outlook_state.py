"""add outlook state

Revision ID: b8f4c2d9a761
Revises: a7d2e9c14b83
Create Date: 2026-10-24 17:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b8f4c2d9a761"
down_revision: str | Sequence[str] | None = "a7d2e9c14b83"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "business_profiles",
        sa.Column(
            "outlook_state",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("business_profiles", "outlook_state")
