from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from back.api.deps import get_current_user
from back.db.models import Company, User
from back.db.session import get_session
from back.schemas.business import BusinessListItem, BusinessOut
from back.schemas.common import Page

router = APIRouter(prefix="/businesses", tags=["businesses"])

PRODUCT_COLUMNS = {
    "rko": Company.cl_product_rko_mark,
    "guarantees": Company.cl_product_gar_mark,
    "loans": Company.cl_product_loa_mark,
    "leasing": Company.cl_product_lea_mark,
    "deposits": Company.cl_product_dep_mark,
    "salary": Company.cl_product_zpp_mark,
    "factoring": Company.factoring_mark,
}


@router.get("", response_model=Page[BusinessListItem])
async def list_businesses(
    search: str | None = Query(default=None, max_length=128),
    city: str | None = None,
    region: str | None = None,
    segment: str | None = None,
    okved: str | None = None,
    product: str | None = None,
    fts: bool | None = None,
    min_revenue: float | None = None,
    max_revenue: float | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> Page[BusinessListItem]:
    filters = []
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Company.uid.ilike(pattern),
                Company.city.ilike(pattern),
                Company.region.ilike(pattern),
                Company.main_okved_name.ilike(pattern),
            )
        )
    if city:
        filters.append(Company.city == city)
    if region:
        filters.append(Company.region == region)
    if segment:
        filters.append(Company.revenue_segment == segment)
    if okved:
        filters.append(Company.main_okved_code.startswith(okved))
    if product and product in PRODUCT_COLUMNS:
        filters.append(PRODUCT_COLUMNS[product].is_(True))
    if fts is not None:
        filters.append(Company.fts_flag.is_(fts))
    if min_revenue is not None:
        filters.append(Company.revenue >= min_revenue)
    if max_revenue is not None:
        filters.append(Company.revenue <= max_revenue)

    total = (
        await session.execute(select(func.count()).select_from(Company).where(*filters))
    ).scalar_one()
    rows = (
        (
            await session.execute(
                select(Company)
                .where(*filters)
                .order_by(Company.revenue.desc().nullslast(), Company.uid)
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )
    return Page[BusinessListItem](
        items=[BusinessListItem.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{uid}", response_model=BusinessOut)
async def get_business(
    uid: str,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> BusinessOut:
    company = await session.get(Company, uid)
    if company is None:
        raise HTTPException(status_code=404, detail="Компания не найдена")
    return BusinessOut.model_validate(company)
