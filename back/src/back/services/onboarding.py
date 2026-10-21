from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from back.core.constants import (
    DEFAULT_BUSINESS_NAME,
    DEFAULT_ENTREPRENEUR_NAME,
    ONBOARDING_ORDER,
    OnboardingStep,
)
from back.db.models import (
    BusinessCategory,
    BusinessProfile,
    Category,
    Company,
    Counterparty,
    ReportingUpload,
    User,
)
from back.schemas.onboarding import OnboardingState, OnboardingStepState, ProfileOut

STEP_TITLES: dict[OnboardingStep, str] = {
    OnboardingStep.REGISTERED: "Регистрация",
    OnboardingStep.BUSINESS_SELECTED: "Выбор компании по UID",
    OnboardingStep.PROFILE_FILLED: "Имя и название бизнеса",
    OnboardingStep.ROLE_SELECTED: "Роль в компании",
    OnboardingStep.COUNTERPARTIES_CONFIGURED: "Контрагенты",
    OnboardingStep.CATEGORIES_CONFIGURED: "Категории влияния",
    OnboardingStep.REPORTING_UPLOADED: "Отчётность",
    OnboardingStep.COMPLETED: "Готово",
}

STEP_RANK = {step: index for index, step in enumerate(ONBOARDING_ORDER)}


def step_rank(value: str | None) -> int:
    try:
        return STEP_RANK[OnboardingStep(value or OnboardingStep.REGISTERED.value)]
    except ValueError:
        return 0


def advance_step(profile: BusinessProfile, step: OnboardingStep) -> None:
    if step_rank(profile.onboarding_step) < STEP_RANK[step]:
        profile.onboarding_step = step.value


def next_step(profile: BusinessProfile | None) -> str:
    if (
        profile is None
        or step_rank(profile.onboarding_step) < STEP_RANK[OnboardingStep.BUSINESS_SELECTED]
    ):
        return OnboardingStep.BUSINESS_SELECTED.value
    if step_rank(profile.onboarding_step) < STEP_RANK[OnboardingStep.PROFILE_FILLED]:
        return OnboardingStep.PROFILE_FILLED.value
    if (
        not profile.role
        or step_rank(profile.onboarding_step) < STEP_RANK[OnboardingStep.ROLE_SELECTED]
    ):
        return OnboardingStep.ROLE_SELECTED.value
    if step_rank(profile.onboarding_step) < STEP_RANK[OnboardingStep.COUNTERPARTIES_CONFIGURED]:
        return OnboardingStep.COUNTERPARTIES_CONFIGURED.value
    if step_rank(profile.onboarding_step) < STEP_RANK[OnboardingStep.CATEGORIES_CONFIGURED]:
        return OnboardingStep.CATEGORIES_CONFIGURED.value
    if step_rank(profile.onboarding_step) < STEP_RANK[OnboardingStep.REPORTING_UPLOADED]:
        return OnboardingStep.REPORTING_UPLOADED.value
    if not profile.onboarding_completed:
        return OnboardingStep.COMPLETED.value
    return OnboardingStep.COMPLETED.value


def build_state(profile: BusinessProfile | None) -> OnboardingState:
    current_rank = step_rank(profile.onboarding_step) if profile else -1
    completed = bool(profile and profile.onboarding_completed)
    steps = [
        OnboardingStepState(
            key=step.value,
            title=STEP_TITLES[step],
            done=current_rank >= STEP_RANK[step]
            or (completed and step is not OnboardingStep.COMPLETED),
            optional=step is OnboardingStep.REPORTING_UPLOADED,
        )
        for step in ONBOARDING_ORDER
        if step is not OnboardingStep.REGISTERED
    ]
    if completed:
        for item in steps:
            item.done = True
    return OnboardingState(
        completed=completed,
        next_step=next_step(profile),
        steps=steps,
        profile=ProfileOut.model_validate(profile) if profile else None,
    )


async def get_profile(
    session: AsyncSession, user: User, with_company: bool = True
) -> BusinessProfile | None:
    query = select(BusinessProfile).where(BusinessProfile.user_id == user.id)
    if with_company:
        query = query.options(selectinload(BusinessProfile.company))
    return (await session.execute(query)).scalar_one_or_none()


async def _reset_derived(session: AsyncSession, profile: BusinessProfile) -> None:
    await session.execute(delete(BusinessCategory).where(BusinessCategory.profile_id == profile.id))
    await session.execute(delete(Counterparty).where(Counterparty.profile_id == profile.id))
    await session.execute(delete(ReportingUpload).where(ReportingUpload.profile_id == profile.id))
    profile.reporting_summary = {}


async def select_business(session: AsyncSession, user: User, company_uid: str) -> BusinessProfile:
    company = await session.get(Company, company_uid)
    if company is None:
        raise LookupError("Компания с таким UID не найдена")

    profile = await get_profile(session, user, with_company=False)
    if profile is None:
        profile = BusinessProfile(
            user_id=user.id,
            company_uid=company.uid,
            entrepreneur_name=DEFAULT_ENTREPRENEUR_NAME,
            business_name=DEFAULT_BUSINESS_NAME,
            tags=company.tags,
            onboarding_step=OnboardingStep.BUSINESS_SELECTED.value,
        )
        session.add(profile)
        await session.flush()
    elif profile.company_uid != company.uid:
        await _reset_derived(session, profile)
        profile.company_uid = company.uid
        profile.tags = company.tags
        profile.role = None
        profile.onboarding_completed = False
        profile.onboarding_step = OnboardingStep.BUSINESS_SELECTED.value
    else:
        advance_step(profile, OnboardingStep.BUSINESS_SELECTED)

    profile.company = company
    await session.commit()
    await session.refresh(profile, attribute_names=["company"])
    return profile


async def update_names(
    session: AsyncSession,
    profile: BusinessProfile,
    entrepreneur_name: str | None,
    business_name: str | None,
) -> BusinessProfile:
    if entrepreneur_name is not None:
        profile.entrepreneur_name = entrepreneur_name.strip() or DEFAULT_ENTREPRENEUR_NAME
    if business_name is not None:
        profile.business_name = business_name.strip() or DEFAULT_BUSINESS_NAME
    advance_step(profile, OnboardingStep.PROFILE_FILLED)
    await session.commit()
    await session.refresh(profile, attribute_names=["company"])
    return profile


async def set_role(session: AsyncSession, profile: BusinessProfile, role: str) -> BusinessProfile:
    profile.role = role
    advance_step(profile, OnboardingStep.ROLE_SELECTED)
    await session.commit()
    await session.refresh(profile, attribute_names=["company"])
    return profile


async def save_categories(
    session: AsyncSession,
    profile: BusinessProfile,
    items: list[dict[str, Any]],
) -> list[BusinessCategory]:
    category_ids = {item["category_id"] for item in items}
    existing = {
        row.category_id: row
        for row in (
            await session.execute(
                select(BusinessCategory).where(BusinessCategory.profile_id == profile.id)
            )
        ).scalars()
    }
    categories = {row.id: row for row in (await session.execute(select(Category))).scalars()}
    for category_id in category_ids:
        if category_id not in categories:
            continue
        row = existing.get(category_id)
        item = next(item for item in items if item["category_id"] == category_id)
        if row is None:
            row = BusinessCategory(
                profile_id=profile.id,
                category_id=category_id,
                weight=float(item["weight"]),
                rationale=str(item.get("rationale") or ""),
                is_manual=False,
            )
            session.add(row)
        else:
            row.weight = float(item["weight"])
            row.rationale = str(item.get("rationale") or row.rationale)
    advance_step(profile, OnboardingStep.CATEGORIES_CONFIGURED)
    await session.commit()
    return list(
        (
            await session.execute(
                select(BusinessCategory)
                .where(BusinessCategory.profile_id == profile.id)
                .order_by(BusinessCategory.weight.desc())
            )
        ).scalars()
    )


async def complete_onboarding(session: AsyncSession, profile: BusinessProfile) -> BusinessProfile:
    missing: list[str] = []
    if not profile.company_uid:
        missing.append("компания")
    if not profile.role:
        missing.append("роль")
    category_count = (
        (
            await session.execute(
                select(BusinessCategory).where(BusinessCategory.profile_id == profile.id)
            )
        )
        .scalars()
        .first()
    )
    if category_count is None:
        missing.append("категории")
    if missing:
        raise ValueError("Не заполнено: " + ", ".join(missing))
    profile.onboarding_completed = True
    profile.onboarding_step = OnboardingStep.COMPLETED.value
    await session.commit()
    await session.refresh(profile, attribute_names=["company"])
    return profile
