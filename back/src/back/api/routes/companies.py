from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from back.api.deps import SessionDep
from back.db.models import Company, CompanyProfile
from back.schemas.api import CompanyProfilePayload

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/{company_id}/profile", response_model=CompanyProfilePayload)
async def get_profile(
    company_id: int,
    session: SessionDep,
) -> CompanyProfilePayload:
    profile = await session.scalar(
        select(CompanyProfile).where(CompanyProfile.company_id == company_id)
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return CompanyProfilePayload.model_validate(
        {
            "description": profile.description,
            "factors": profile.factors or [],
            "entities": profile.entities or [],
        }
    )


@router.put("/{company_id}/profile", response_model=CompanyProfilePayload)
async def put_profile(
    company_id: int,
    payload: CompanyProfilePayload,
    session: SessionDep,
) -> CompanyProfilePayload:
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    profile = await session.scalar(
        select(CompanyProfile).where(CompanyProfile.company_id == company_id)
    )
    factors = [factor.model_dump() for factor in payload.factors]
    entities = [entity.model_dump() for entity in payload.entities]
    if profile is None:
        profile = CompanyProfile(
            company_id=company_id,
            description=payload.description,
            factors=factors,
            entities=entities,
        )
        session.add(profile)
    else:
        profile.description = payload.description
        profile.factors = factors
        profile.entities = entities
    company.description = payload.description
    await session.commit()
    return payload
