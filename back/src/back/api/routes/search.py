from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from back.api.deps import get_current_profile
from back.db.models import BusinessProfile
from back.db.session import get_session
from back.schemas.search import SearchHistoryResponse, SearchResponse
from back.services.search import clear_history, remove_history, search, search_history

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def global_search(
    q: str = Query(default="", max_length=200),
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> SearchResponse:
    return await search(session, profile, q)


@router.get("/history", response_model=SearchHistoryResponse)
async def get_history(
    profile: BusinessProfile = Depends(get_current_profile),
) -> SearchHistoryResponse:
    return search_history(profile)


@router.delete("/history", response_model=SearchHistoryResponse)
async def delete_history(
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> SearchHistoryResponse:
    clear_history(profile)
    await session.commit()
    return search_history(profile)


@router.delete("/history/{item_id}", response_model=SearchHistoryResponse)
async def delete_history_item(
    item_id: str,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> SearchHistoryResponse:
    if not remove_history(profile, item_id):
        raise HTTPException(status_code=404, detail="Запрос не найден в истории")
    await session.commit()
    return search_history(profile)
