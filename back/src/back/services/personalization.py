from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from back.db.models import BusinessCategory, BusinessProfile, Counterparty, Feedback, TrackedItem


async def load_categories(
    session: AsyncSession, profile: BusinessProfile
) -> list[BusinessCategory]:
    return list(
        (
            await session.execute(
                select(BusinessCategory)
                .options(selectinload(BusinessCategory.category))
                .where(BusinessCategory.profile_id == profile.id)
            )
        ).scalars()
    )


async def load_counterparties(
    session: AsyncSession, profile: BusinessProfile
) -> list[Counterparty]:
    return list(
        (
            await session.execute(
                select(Counterparty)
                .where(Counterparty.profile_id == profile.id)
                .order_by(Counterparty.importance.desc())
            )
        ).scalars()
    )


async def load_tracked_ids(session: AsyncSession, profile: BusinessProfile) -> set[UUID]:
    rows = await session.execute(
        select(TrackedItem.event_id).where(TrackedItem.profile_id == profile.id)
    )
    return set(rows.scalars())


async def load_skipped_ids(session: AsyncSession, profile: BusinessProfile) -> set[UUID]:
    rows = await session.execute(
        select(Feedback.event_id).where(
            Feedback.profile_id == profile.id,
            Feedback.action.in_(["skip", "not_relevant"]),
        )
    )
    return set(rows.scalars())
