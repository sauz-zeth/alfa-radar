"""dynamic source recommendations and RSS popularity

Revision ID: e5c6d7e8f9a0
Revises: d1e2f3a4b5c6
Create Date: 2026-10-25

"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from back.core.recommendations import recommend_ids
from back.core.sources import CHANNELS

revision: str = "e5c6d7e8f9a0"
down_revision: str | Sequence[str] | None = "d1e2f3a4b5c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    upsert = sa.text(
        """
        INSERT INTO channels (id, name, handle, topics, kind, is_recommended, is_active, meta)
        VALUES (:id, :name, :handle, :topics, 'catalog', false, true, CAST(:meta AS jsonb))
        ON CONFLICT (id) DO UPDATE SET
            meta = channels.meta || EXCLUDED.meta
        """
    )
    for item in CHANNELS:
        meta = {}
        if item.feed_url:
            meta["feed_url"] = item.feed_url
        if item.subscribers is not None:
            meta["tg_subscribers"] = item.subscribers
        if item.popularity is not None:
            meta["rss_popularity"] = item.popularity
        bind.execute(
            upsert,
            {
                "id": item.id,
                "name": item.name,
                "handle": item.handle,
                "topics": item.topics,
                "meta": json.dumps(meta, ensure_ascii=False),
            },
        )

    bind.execute(sa.text("DELETE FROM profile_channels WHERE source = 'recommended'"))

    profiles = list(bind.execute(sa.text("SELECT id FROM business_profiles")).scalars())
    category_sql = sa.text(
        "SELECT category_id FROM business_categories WHERE profile_id = :profile_id"
    )
    subscribe = sa.text(
        """
        INSERT INTO profile_channels (id, profile_id, channel_id, source)
        VALUES (gen_random_uuid(), :profile_id, :channel_id, 'recommended')
        ON CONFLICT (profile_id, channel_id) DO NOTHING
        """
    )
    for profile_id in profiles:
        category_ids = set(bind.execute(category_sql, {"profile_id": profile_id}).scalars())
        for channel_id in recommend_ids(category_ids):
            bind.execute(
                subscribe,
                {"profile_id": profile_id, "channel_id": channel_id},
            )

    bind.execute(sa.text("UPDATE business_profiles SET sources_initialized = true"))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM profile_channels WHERE source = 'recommended'"))
    bind.execute(sa.text("UPDATE business_profiles SET sources_initialized = false"))
