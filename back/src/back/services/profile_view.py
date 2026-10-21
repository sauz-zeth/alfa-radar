from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from back.db.models import BusinessCategory, BusinessProfile, Counterparty
from back.schemas.onboarding import CategoryOut, CounterpartyOut


async def categories_out(session: AsyncSession, profile: BusinessProfile) -> list[CategoryOut]:
    rows = (
        (
            await session.execute(
                select(BusinessCategory)
                .options(selectinload(BusinessCategory.category))
                .where(BusinessCategory.profile_id == profile.id)
                .order_by(BusinessCategory.weight.desc(), BusinessCategory.category_id)
            )
        )
        .scalars()
        .all()
    )
    return [
        CategoryOut(
            category_id=row.category_id,
            slug=row.category.slug,
            name=row.category.name,
            short_name=row.category.short_name,
            group=row.category.group,
            description=row.category.description,
            example=row.category.example,
            channels=list(row.category.channels or []),
            weight=row.weight,
            rationale=row.rationale,
            is_manual=row.is_manual,
        )
        for row in rows
        if row.category is not None
    ]


async def counterparties_out(
    session: AsyncSession, profile: BusinessProfile
) -> list[CounterpartyOut]:
    rows = (
        (
            await session.execute(
                select(Counterparty)
                .where(Counterparty.profile_id == profile.id)
                .order_by(Counterparty.importance.desc())
            )
        )
        .scalars()
        .all()
    )
    return [CounterpartyOut.model_validate(row) for row in rows]
