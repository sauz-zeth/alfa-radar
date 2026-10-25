"""add RSS catalog and telegram subscriber counts

Revision ID: d1e2f3a4b5c6
Revises: c9a4f1e2b7d3
Create Date: 2026-10-25

"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from back.core.sources import CHANNELS, RECOMMENDED_IDS

revision: str = "d1e2f3a4b5c6"
down_revision: str | Sequence[str] | None = "c9a4f1e2b7d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    channel_ids = [item.id for item in CHANNELS]

    bind.execute(
        sa.text(
            """
            DELETE FROM channels
            WHERE kind = 'catalog' AND id NOT IN :ids
            """
        ).bindparams(sa.bindparam("ids", expanding=True)),
        {"ids": channel_ids},
    )

    upsert = sa.text(
        """
        INSERT INTO channels (id, name, handle, topics, kind, is_recommended, is_active, meta)
        VALUES (:id, :name, :handle, :topics, 'catalog', :recommended, true, CAST(:meta AS jsonb))
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            handle = EXCLUDED.handle,
            topics = EXCLUDED.topics,
            kind = 'catalog',
            is_recommended = EXCLUDED.is_recommended,
            is_active = true,
            meta = channels.meta || EXCLUDED.meta
        """
    )
    for item in CHANNELS:
        meta = {}
        if item.feed_url:
            meta["feed_url"] = item.feed_url
        if item.subscribers is not None:
            meta["tg_subscribers"] = item.subscribers
        bind.execute(
            upsert,
            {
                "id": item.id,
                "name": item.name,
                "handle": item.handle,
                "topics": item.topics,
                "recommended": item.id in RECOMMENDED_IDS,
                "meta": json.dumps(meta, ensure_ascii=False),
            },
        )


def downgrade() -> None:
    op.get_bind().execute(sa.text("DELETE FROM channels WHERE kind = 'catalog' AND id LIKE 'rss\\_%'"))
