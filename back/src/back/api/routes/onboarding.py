from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from back.api.deps import get_current_profile, get_current_user
from back.config import get_settings
from back.core.constants import OnboardingStep, ReportingForm
from back.db.models import BusinessCategory, BusinessProfile, Counterparty, ReportingUpload, User
from back.db.session import get_session
from back.schemas.business import BusinessSelectRequest
from back.schemas.onboarding import (
    CategoryOut,
    CategoryWeightRequest,
    CounterpartyOut,
    CounterpartyRenameBatch,
    OnboardingState,
    ProfileUpdateRequest,
    ReportingResponse,
    ReportingUploadOut,
    RoleRequest,
    SkipStepRequest,
)
from back.services.categories import suggest_categories
from back.services.counterparties import build_counterparties
from back.services.onboarding import (
    advance_step,
    build_state,
    complete_onboarding,
    get_profile,
    save_categories,
    select_business,
    set_role,
    update_names,
)
from back.services.profile_view import categories_out, counterparties_out
from back.services.reporting import process_upload

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


async def _state(session: AsyncSession, user: User) -> OnboardingState:
    profile = await get_profile(session, user)
    return build_state(profile)


@router.get("/state", response_model=OnboardingState)
async def state(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> OnboardingState:
    return await _state(session, user)


@router.post("/business", response_model=OnboardingState)
async def choose_business(
    payload: BusinessSelectRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> OnboardingState:
    try:
        await select_business(session, user, payload.uid)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return await _state(session, user)


@router.patch("/profile", response_model=OnboardingState)
async def update_profile(
    payload: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> OnboardingState:
    profile = await get_profile(session, user)
    if profile is None:
        raise HTTPException(status_code=409, detail="Сначала выберите бизнес")
    await update_names(session, profile, payload.entrepreneur_name, payload.business_name)
    return await _state(session, user)


@router.post("/role", response_model=OnboardingState)
async def choose_role(
    payload: RoleRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> OnboardingState:
    profile = await get_profile(session, user)
    if profile is None:
        raise HTTPException(status_code=409, detail="Сначала выберите бизнес")
    await set_role(session, profile, payload.role.value)
    return await _state(session, user)


@router.post("/skip", response_model=OnboardingState)
async def skip_step(
    payload: SkipStepRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> OnboardingState:
    profile = await get_profile(session, user)
    if profile is None:
        raise HTTPException(status_code=409, detail="Сначала выберите бизнес")
    step = payload.step.strip()
    if step == OnboardingStep.PROFILE_FILLED.value:
        advance_step(profile, OnboardingStep.PROFILE_FILLED)
    elif step == OnboardingStep.REPORTING_UPLOADED.value:
        advance_step(profile, OnboardingStep.REPORTING_UPLOADED)
    else:
        raise HTTPException(status_code=400, detail="Этот шаг нельзя пропустить")
    await session.commit()
    return await _state(session, user)


@router.get("/counterparties", response_model=list[CounterpartyOut])
async def list_counterparties(
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> list[CounterpartyOut]:
    rows = await build_counterparties(session, profile, use_llm=get_settings().llm_ml_enabled)
    advance_step(profile, OnboardingStep.COUNTERPARTIES_CONFIGURED)
    await session.commit()
    return [CounterpartyOut.model_validate(row) for row in rows]


@router.post("/counterparties/suggest", response_model=list[CounterpartyOut])
async def suggest_counterparties(
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> list[CounterpartyOut]:
    rows = await build_counterparties(session, profile, use_llm=get_settings().llm_ml_enabled)
    advance_step(profile, OnboardingStep.COUNTERPARTIES_CONFIGURED)
    await session.commit()
    return [CounterpartyOut.model_validate(row) for row in rows]


@router.patch("/counterparties", response_model=list[CounterpartyOut])
async def rename_counterparties(
    payload: CounterpartyRenameBatch,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> list[CounterpartyOut]:
    rows = {
        row.id: row
        for row in (
            await session.execute(select(Counterparty).where(Counterparty.profile_id == profile.id))
        ).scalars()
    }
    for item in payload.items:
        row = rows.get(item.id)
        if row is not None:
            row.custom_name = (item.name or "").strip() or None
    advance_step(profile, OnboardingStep.COUNTERPARTIES_CONFIGURED)
    await session.commit()
    return await counterparties_out(session, profile)


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> list[CategoryOut]:
    return await categories_out(session, profile)


@router.post("/categories/suggest", response_model=list[CategoryOut])
async def suggest_profile_categories(
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> list[CategoryOut]:
    if not profile.company:
        raise HTTPException(status_code=409, detail="Сначала выберите бизнес")
    items = await suggest_categories(profile.company, use_llm=get_settings().llm_ml_enabled)
    await save_categories(session, profile, items)
    return await categories_out(session, profile)


@router.patch("/categories/{category_id}", response_model=list[CategoryOut])
async def update_category_weight(
    category_id: int,
    payload: CategoryWeightRequest,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> list[CategoryOut]:
    row = (
        await session.execute(
            select(BusinessCategory).where(
                BusinessCategory.profile_id == profile.id,
                BusinessCategory.category_id == category_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Категория не настроена в профиле")
    row.weight = payload.weight
    row.is_manual = True
    advance_step(profile, OnboardingStep.CATEGORIES_CONFIGURED)
    await session.commit()
    return await categories_out(session, profile)


@router.get("/reporting", response_model=ReportingResponse)
async def list_reporting(
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> ReportingResponse:
    rows = (
        (
            await session.execute(
                select(ReportingUpload)
                .where(ReportingUpload.profile_id == profile.id)
                .order_by(ReportingUpload.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return ReportingResponse(
        uploads=[ReportingUploadOut.model_validate(row) for row in rows],
        summary=profile.reporting_summary or {},
        accepted_forms=[item.value for item in ReportingForm],
    )


@router.post("/reporting", response_model=ReportingResponse)
async def upload_reporting(
    balance: UploadFile | None = File(default=None),
    income: UploadFile | None = File(default=None),
    cash_flow: UploadFile | None = File(default=None),
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> ReportingResponse:
    files = {
        ReportingForm.BALANCE: balance,
        ReportingForm.INCOME: income,
        ReportingForm.CASH_FLOW: cash_flow,
    }
    uploads: list[ReportingUploadOut] = []
    for form_type, upload in files.items():
        if upload is None:
            continue
        row = await process_upload(
            session,
            profile,
            form_type,
            upload,
            use_llm=get_settings().llm_ml_enabled,
        )
        uploads.append(ReportingUploadOut.model_validate(row))
    if not uploads:
        raise HTTPException(status_code=400, detail="Загрузите хотя бы одну форму отчётности")
    advance_step(profile, OnboardingStep.REPORTING_UPLOADED)
    await session.commit()
    return ReportingResponse(
        uploads=uploads,
        summary=profile.reporting_summary or {},
        accepted_forms=[item.value for item in ReportingForm],
    )


@router.post("/complete", response_model=OnboardingState)
async def finish_onboarding(
    user: User = Depends(get_current_user),
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> OnboardingState:
    try:
        await complete_onboarding(session, profile)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return await _state(session, user)
