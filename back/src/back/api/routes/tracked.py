from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from back.api.deps import get_current_profile
from back.db.models import BusinessProfile, NewsEvent, TrackedItem
from back.db.session import get_session
from back.schemas.feed import AgentReanalyzeRequest, TrackedItemOut, TrackedListResponse
from back.services.agent import analyze_event
from back.services.feed import event_to_feed_item, match_event
from back.services.personalization import load_categories, load_counterparties

router = APIRouter(prefix="/tracked", tags=["tracked"])


def _out(item: TrackedItem, feed_item) -> TrackedItemOut:
    return TrackedItemOut(
        id=item.id,
        event_id=item.event_id,
        status=item.status,
        report=item.report,
        created_at=item.created_at,
        updated_at=item.updated_at,
        event=feed_item,
    )


async def _load_tracked(
    session: AsyncSession, profile: BusinessProfile, item_id: UUID | None = None
) -> list[TrackedItem]:
    query = (
        select(TrackedItem)
        .options(selectinload(TrackedItem.event))
        .where(TrackedItem.profile_id == profile.id)
    )
    if item_id is not None:
        query = query.where(TrackedItem.id == item_id)
    return list((await session.execute(query.order_by(TrackedItem.updated_at.desc()))).scalars())


@router.get("", response_model=TrackedListResponse)
async def list_tracked(
    status_filter: str = Query(default="active", alias="status"),
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> TrackedListResponse:
    rows = await _load_tracked(session, profile)
    if status_filter != "all":
        rows = [row for row in rows if row.status == status_filter]
    categories = await load_categories(session, profile)
    counterparties = await load_counterparties(session, profile)
    items = []
    for row in rows:
        match = match_event(row.event, categories, counterparties)
        items.append(_out(row, event_to_feed_item(row.event, match, is_tracked=True)))
    return TrackedListResponse(items=items, total=len(items))


@router.get("/{item_id}", response_model=TrackedItemOut)
async def get_tracked(
    item_id: UUID,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> TrackedItemOut:
    rows = await _load_tracked(session, profile, item_id)
    if not rows:
        raise HTTPException(status_code=404, detail="Отслеживаемая новость не найдена")
    row = rows[0]
    categories = await load_categories(session, profile)
    counterparties = await load_counterparties(session, profile)
    match = match_event(row.event, categories, counterparties)
    return _out(row, event_to_feed_item(row.event, match, is_tracked=True))


@router.delete("/{item_id}", status_code=204)
async def untrack(
    item_id: UUID,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> None:
    row = await session.get(TrackedItem, item_id)
    if row is None or row.profile_id != profile.id:
        raise HTTPException(status_code=404, detail="Отслеживаемая новость не найдена")
    await session.delete(row)
    await session.commit()


@router.post("/{item_id}/reanalyze", response_model=TrackedItemOut)
async def reanalyze(
    item_id: UUID,
    payload: AgentReanalyzeRequest | None = None,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> TrackedItemOut:
    row = await session.get(TrackedItem, item_id)
    if row is None or row.profile_id != profile.id:
        raise HTTPException(status_code=404, detail="Отслеживаемая новость не найдена")
    event = await session.get(NewsEvent, row.event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Новость не найдена")
    categories = await load_categories(session, profile)
    counterparties = await load_counterparties(session, profile)
    match = match_event(event, categories, counterparties)
    report = await analyze_event(
        profile=profile,
        event=event,
        business_categories=categories,
        counterparties=counterparties,
        match_importance=match.importance,
        matched_counterparties=match.matched_counterparties,
    )
    if payload and payload.question:
        report["user_question"] = payload.question
        report["agent_steps"] = [
            *report.get("agent_steps", []),
            {"type": "Данные", "text": f"Учтён уточняющий вопрос: {payload.question}"},
        ]
    row.report = report
    await session.commit()
    await session.refresh(row)
    return _out(row, event_to_feed_item(event, match, is_tracked=True))
