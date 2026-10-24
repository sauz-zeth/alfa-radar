from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from back.api.deps import get_current_profile
from back.db.models import BusinessProfile, Counterparty, NewsEvent
from back.db.session import get_session
from back.schemas.outlook import (
    OutlookConnectRequest,
    OutlookContactList,
    OutlookMessageCreate,
    OutlookMessageOut,
    OutlookMessagePatch,
    OutlookStateOut,
)
from back.services import outlook as service

router = APIRouter(prefix="/outlook", tags=["outlook"])


def _fail(exc: service.OutlookError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get("", response_model=OutlookStateOut)
async def get_outlook(
    event_id: UUID | None = Query(default=None),
    profile: BusinessProfile = Depends(get_current_profile),
) -> OutlookStateOut:
    return service.get_state(profile, str(event_id) if event_id else None)


@router.post("/connect", response_model=OutlookStateOut)
async def connect_outlook(
    payload: OutlookConnectRequest,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> OutlookStateOut:
    try:
        state = service.connect(profile, payload)
    except service.OutlookError as exc:
        raise _fail(exc) from exc
    await session.commit()
    return state


@router.post("/disconnect", response_model=OutlookStateOut)
async def disconnect_outlook(
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> OutlookStateOut:
    state = service.disconnect(profile)
    await session.commit()
    return state


@router.get("/contacts", response_model=OutlookContactList)
async def list_contacts(
    q: str = Query(default="", max_length=128),
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> OutlookContactList:
    counterparties = list(
        (
            await session.execute(
                select(Counterparty).where(Counterparty.profile_id == profile.id)
            )
        )
        .scalars()
        .all()
    )
    return OutlookContactList(items=service.contacts(profile, counterparties, q))


@router.post("/messages", response_model=OutlookMessageOut)
async def create_message(
    payload: OutlookMessageCreate,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> OutlookMessageOut:
    event = await session.get(NewsEvent, payload.event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    try:
        message = service.create_message(profile, payload)
    except service.OutlookError as exc:
        raise _fail(exc) from exc
    await session.commit()
    return message


@router.patch("/messages/{message_id}", response_model=OutlookMessageOut)
async def update_message(
    message_id: str,
    payload: OutlookMessagePatch,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> OutlookMessageOut:
    try:
        message = service.update_message(profile, message_id, payload)
    except service.OutlookError as exc:
        raise _fail(exc) from exc
    await session.commit()
    return message


@router.delete("/messages/{message_id}", status_code=204)
async def delete_message(
    message_id: str,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> Response:
    try:
        service.delete_message(profile, message_id)
    except service.OutlookError as exc:
        raise _fail(exc) from exc
    await session.commit()
    return Response(status_code=204)


@router.post("/messages/{message_id}/send", response_model=OutlookMessageOut)
async def send_message(
    message_id: str,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> OutlookMessageOut:
    try:
        message = service.send_message(profile, message_id)
    except service.OutlookError as exc:
        raise _fail(exc) from exc
    await session.commit()
    return message


@router.post("/messages/{message_id}/remind", response_model=OutlookMessageOut)
async def remind_message(
    message_id: str,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> OutlookMessageOut:
    try:
        message = service.remind(profile, message_id)
    except service.OutlookError as exc:
        raise _fail(exc) from exc
    await session.commit()
    return message


@router.post("/messages/{message_id}/advance", response_model=OutlookMessageOut)
async def advance_message(
    message_id: str,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> OutlookMessageOut:
    try:
        message = service.advance(profile, message_id)
    except service.OutlookError as exc:
        raise _fail(exc) from exc
    await session.commit()
    return message
