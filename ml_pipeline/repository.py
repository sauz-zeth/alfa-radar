"""Database operations for the ML feed worker."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from back.db.models import (
    BusinessCategory,
    BusinessProfile,
    Category,
    Channel,
    EventAnalysis,
    NewsEvent,
    Post,
    ProfileChannel,
    ProfileEventScore,
)
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession


class PostRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def claim_batch(self, limit: int, lease_seconds: int) -> list[Post]:
        now = datetime.now(UTC)
        posts = list(
            (
                await self.session.execute(
                    select(Post)
                    .where(Post.status.in_(["received", "retry", "processing"]))
                    .where((Post.lease_until.is_(None)) | (Post.lease_until <= now))
                    .order_by(Post.published_at, Post.id)
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
            ).scalars()
        )
        for post in posts:
            post.status = "processing"
            post.lease_until = now + timedelta(seconds=lease_seconds)
            post.status_updated_at = now
        await self.session.flush()
        return posts

    async def mark_retry(self, post_id: UUID, error: str, delay_seconds: int) -> None:
        await self.session.execute(
            update(Post)
            .where(Post.id == post_id)
            .values(
                status="retry",
                lease_until=datetime.now(UTC) + timedelta(seconds=delay_seconds),
                attempt_count=Post.attempt_count + 1,
                last_error=error[:2000],
                status_updated_at=datetime.now(UTC),
            )
        )

    async def mark_failed(self, post_id: UUID, error: str) -> None:
        await self.session.execute(
            update(Post)
            .where(Post.id == post_id)
            .values(
                status="failed",
                lease_until=None,
                attempt_count=Post.attempt_count + 1,
                last_error=error[:2000],
                status_updated_at=datetime.now(UTC),
            )
        )

    async def mark_clustered(
        self,
        post: Post,
        event: NewsEvent,
        cluster_key: str,
        labels: list[dict[str, Any]],
        embedding: list[float],
    ) -> None:
        post.status = "clustered"
        post.stage = "clustered"
        post.lease_until = None
        post.last_error = None
        post.news_event_id = event.id
        post.cluster_key = cluster_key
        post.categories = labels
        post.embedding = embedding
        post.status_updated_at = datetime.now(UTC)

    async def lock_cluster(self, key: str) -> None:
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": key}
        )

    async def cluster_posts(self, since: datetime) -> list[Post]:
        return list(
            (
                await self.session.execute(
                    select(Post)
                    .where(
                        Post.status == "clustered",
                        Post.news_event_id.is_not(None),
                        Post.published_at >= since,
                    )
                    .order_by(Post.published_at)
                )
            ).scalars()
        )

    async def candidate_events(self, since: datetime) -> list[tuple[NewsEvent, datetime]]:
        rows = await self.session.execute(
            select(NewsEvent, func.max(Post.published_at).label("last_seen_at"))
            .join(Post, Post.news_event_id == NewsEvent.id)
            .where(NewsEvent.is_active.is_(True), Post.status == "clustered")
            .group_by(NewsEvent.id)
            .having(func.max(Post.published_at) >= since)
            .order_by(func.max(Post.published_at).desc())
        )
        return list(rows.all())

    async def event_member_posts(self, event_ids: list[UUID], since: datetime) -> list[Post]:
        if not event_ids:
            return []
        return list(
            (
                await self.session.execute(
                    select(Post).where(
                        Post.news_event_id.in_(event_ids),
                        Post.published_at >= since,
                        Post.status == "clustered",
                        Post.embedding.is_not(None),
                    )
                )
            ).scalars()
        )

    async def profiles(self) -> list[BusinessProfile]:
        return list(
            (
                await self.session.execute(select(BusinessProfile).order_by(BusinessProfile.id))
            ).scalars()
        )

    async def profile_categories(self, profile_id: UUID) -> dict[str, float]:
        rows = (
            await self.session.execute(
                select(Category.name, BusinessCategory.weight)
                .join(BusinessCategory, BusinessCategory.category_id == Category.id)
                .where(BusinessCategory.profile_id == profile_id, BusinessCategory.weight > 0)
            )
        ).all()
        return {name: float(weight) for name, weight in rows}

    async def category_ids(self) -> dict[str, int]:
        rows = (await self.session.execute(select(Category.name, Category.id))).all()
        return {name: category_id for name, category_id in rows}

    async def upsert_analysis(
        self, profile_id: UUID, event_id: UUID, values: dict[str, Any]
    ) -> None:
        row = (
            await self.session.execute(
                select(EventAnalysis).where(
                    EventAnalysis.profile_id == profile_id, EventAnalysis.event_id == event_id
                )
            )
        ).scalar_one_or_none()
        if row is None:
            self.session.add(EventAnalysis(profile_id=profile_id, event_id=event_id, **values))
        else:
            for key, value in values.items():
                setattr(row, key, value)

    async def upsert_profile_score(
        self, profile_id: UUID, event_id: UUID, values: dict[str, Any]
    ) -> None:
        row = (
            await self.session.execute(
                select(ProfileEventScore).where(
                    ProfileEventScore.profile_id == profile_id,
                    ProfileEventScore.event_id == event_id,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            self.session.add(ProfileEventScore(profile_id=profile_id, event_id=event_id, **values))
        else:
            for key, value in values.items():
                setattr(row, key, value)

    async def event_source_count(self, event_id: UUID, profile_id: UUID) -> int:
        rows = (
            await self.session.execute(
                select(Post.source_name, Channel.meta)
                .outerjoin(Channel, Channel.name == Post.source_name)
                .where(Post.news_event_id == event_id)
            )
        ).all()
        subscribed_rows = (
            await self.session.execute(
                select(Channel.name, Channel.meta)
                .join(ProfileChannel, ProfileChannel.channel_id == Channel.id)
                .where(ProfileChannel.profile_id == profile_id)
            )
        ).all()
        subscribed = {name for name, _ in subscribed_rows}
        groups = set()
        for name, metadata in rows:
            if not name or (subscribed and name not in subscribed):
                continue
            metadata = metadata or {}
            groups.add(metadata.get("source_group") or metadata.get("original_source") or name)
        return len(groups)
