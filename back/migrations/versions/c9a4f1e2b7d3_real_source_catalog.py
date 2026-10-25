"""replace demo channels with the real source catalog

Revision ID: c9a4f1e2b7d3
Revises: b8f4c2d9a761
Create Date: 2026-10-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from back.core.sources import CHANNELS, RECOMMENDED_IDS

revision: str = "c9a4f1e2b7d3"
down_revision: str | Sequence[str] | None = "b8f4c2d9a761"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    channel_ids = [item.id for item in CHANNELS]

    affected_profiles = list(
        bind.execute(
            sa.text(
                """
                SELECT DISTINCT pc.profile_id
                FROM profile_channels pc
                JOIN channels c ON c.id = pc.channel_id
                WHERE c.kind = 'catalog' AND c.id NOT IN :ids
                """
            ).bindparams(sa.bindparam("ids", expanding=True)),
            {"ids": channel_ids},
        ).scalars()
    )

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
        VALUES (:id, :name, :handle, :topics, 'catalog', :recommended, true, '{}'::jsonb)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            handle = EXCLUDED.handle,
            topics = EXCLUDED.topics,
            kind = 'catalog',
            is_recommended = EXCLUDED.is_recommended,
            is_active = true
        """
    )
    for item in CHANNELS:
        bind.execute(
            upsert,
            {
                "id": item.id,
                "name": item.name,
                "handle": item.handle,
                "topics": item.topics,
                "recommended": item.id in RECOMMENDED_IDS,
            },
        )

    subscribe = sa.text(
        """
        INSERT INTO profile_channels (id, profile_id, channel_id, source)
        VALUES (gen_random_uuid(), :profile_id, :channel_id, 'recommended')
        ON CONFLICT (profile_id, channel_id) DO NOTHING
        """
    )
    for profile_id in affected_profiles:
        for channel_id in RECOMMENDED_IDS:
            bind.execute(
                subscribe,
                {"profile_id": profile_id, "channel_id": channel_id},
            )


def downgrade() -> None:
    # Data-only migration: the previous demo catalog is intentionally not restored.
    pass
