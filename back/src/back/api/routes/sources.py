from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from back.api.deps import get_current_profile
from back.db.models import BusinessProfile
from back.db.session import get_session
from back.schemas.sources import ChannelAddRequest, ChannelCatalogResponse, SourcesState
from back.services.sources import (
    catalog,
    restore_recommended,
    sources_state,
    subscribe,
    unsubscribe,
    unsubscribe_all,
)

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=SourcesState)
async def get_sources(
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> SourcesState:
    state = await sources_state(session, profile)
    await session.commit()
    return state


@router.get("/catalog", response_model=ChannelCatalogResponse)
async def get_catalog(
    q: str = Query(default="", max_length=200),
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> ChannelCatalogResponse:
    result = await catalog(session, profile, q)
    await session.commit()
    return result


@router.post("/channels", response_model=SourcesState)
async def add_channel(
    payload: ChannelAddRequest,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> SourcesState:
    try:
        state = await subscribe(session, profile, payload.query)
    except LookupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return state


@router.post("/channels/{channel_id}/subscribe", response_model=SourcesState)
async def subscribe_channel(
    channel_id: str,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> SourcesState:
    try:
        state = await subscribe(session, profile, channel_id)
    except LookupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return state


@router.delete("/channels/{channel_id}", response_model=SourcesState)
async def unsubscribe_channel(
    channel_id: str,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> SourcesState:
    state = await unsubscribe(session, profile, channel_id)
    await session.commit()
    return state


@router.post("/channels/unsubscribe-all", response_model=SourcesState)
async def unsubscribe_everything(
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> SourcesState:
    state = await unsubscribe_all(session, profile)
    await session.commit()
    return state


@router.post("/channels/restore", response_model=SourcesState)
async def restore_channels(
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> SourcesState:
    state = await restore_recommended(session, profile)
    await session.commit()
    return state
