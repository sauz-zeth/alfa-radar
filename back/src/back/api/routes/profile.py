from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from back.api.deps import get_current_profile
from back.core.constants import ReportingForm
from back.db.models import BusinessCategory, BusinessProfile, Counterparty, ReportingUpload
from back.db.session import get_session
from back.schemas.onboarding import (
    CategoryWeightRequest,
    CounterpartyOut,
    CounterpartyRenameRequest,
    ProfileOut,
    ProfileUpdateRequest,
    ReportingResponse,
    ReportingUploadOut,
)
from back.schemas.profile import ProfileBundle
from back.services.profile_view import categories_out, counterparties_out
from back.services.reporting import process_upload

router = APIRouter(prefix="/profile", tags=["profile"])


async def _bundle(session: AsyncSession, profile: BusinessProfile) -> ProfileBundle:
    return ProfileBundle(
        profile=ProfileOut.model_validate(profile),
        categories=await categories_out(session, profile),
        counterparties=await counterparties_out(session, profile),
        reporting=profile.reporting_summary or {},
    )


@router.get("", response_model=ProfileBundle)
async def get_profile_bundle(
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> ProfileBundle:
    return await _bundle(session, profile)


@router.patch("", response_model=ProfileBundle)
async def update_profile(
    payload: ProfileUpdateRequest,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> ProfileBundle:
    if payload.entrepreneur_name is not None:
        profile.entrepreneur_name = payload.entrepreneur_name.strip() or profile.entrepreneur_name
    if payload.business_name is not None:
        profile.business_name = payload.business_name.strip() or profile.business_name
    if payload.role is not None:
        profile.role = payload.role.value
    await session.commit()
    return await _bundle(session, profile)


@router.get("/categories")
async def get_categories(
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
):
    return await categories_out(session, profile)


@router.patch("/categories/{category_id}")
async def set_category_weight(
    category_id: int,
    payload: CategoryWeightRequest,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
):
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
    await session.commit()
    return await categories_out(session, profile)


@router.get("/counterparties", response_model=list[CounterpartyOut])
async def get_counterparties(
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> list[CounterpartyOut]:
    return await counterparties_out(session, profile)


@router.patch("/counterparties/{counterparty_id}", response_model=list[CounterpartyOut])
async def rename_counterparty(
    counterparty_id: UUID,
    payload: CounterpartyRenameRequest,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> list[CounterpartyOut]:
    row = await session.get(Counterparty, counterparty_id)
    if row is None or row.profile_id != profile.id:
        raise HTTPException(status_code=404, detail="Контрагент не найден")
    row.custom_name = (payload.name or "").strip() or None
    await session.commit()
    return await counterparties_out(session, profile)


@router.get("/reporting", response_model=ReportingResponse)
async def get_reporting(
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
        row = await process_upload(session, profile, form_type, upload)
        uploads.append(ReportingUploadOut.model_validate(row))
    if not uploads:
        raise HTTPException(status_code=400, detail="Загрузите хотя бы одну форму отчётности")
    await session.commit()
    return ReportingResponse(
        uploads=uploads,
        summary=profile.reporting_summary or {},
        accepted_forms=[item.value for item in ReportingForm],
    )
