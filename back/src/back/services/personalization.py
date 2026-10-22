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
        select(TrackedItem.event_id, TrackedItem.event_ids).where(
            TrackedItem.profile_id == profile.id
        )
    )
    result: set[UUID] = set()
    for event_id, event_ids in rows:
        result.add(event_id)
        for raw in event_ids or []:
            try:
                result.add(UUID(str(raw)))
            except ValueError:
                continue
    return result


async def load_skipped_ids(session: AsyncSession, profile: BusinessProfile) -> set[UUID]:
    rows = await session.execute(
        select(Feedback.event_id).where(
            Feedback.profile_id == profile.id,
            Feedback.action.in_(["skip", "not_relevant"]),
        )
    )
    return set(rows.scalars())
