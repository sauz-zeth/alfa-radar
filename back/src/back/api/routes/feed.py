from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from back.api.deps import get_current_profile
from back.core.constants import Impact
from back.db.models import BusinessProfile, Feedback, NewsEvent, TrackedItem
from back.db.session import get_session
from back.schemas.common import Page
from back.schemas.feed import (
    FeedbackRequest,
    FeedItem,
    FeedItemDetail,
    TrackedItemOut,
)
from back.services.agent import analyze_event
from back.services.feed import event_to_feed_item, match_event, recency_key
from back.services.personalization import (
    load_categories,
    load_counterparties,
    load_skipped_ids,
    load_tracked_ids,
)

router = APIRouter(prefix="/feed", tags=["feed"])


@router.get("", response_model=Page[FeedItem])
async def get_feed(
    impact: Impact | None = None,
    category: int | None = Query(default=None, ge=1, le=30),
    q: str | None = Query(default=None, max_length=200),
    include_tracked: bool = False,
    include_skipped: bool = False,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> Page[FeedItem]:
    categories = await load_categories(session, profile)
    counterparties = await load_counterparties(session, profile)
    tracked_ids = await load_tracked_ids(session, profile)
    skipped_ids = await load_skipped_ids(session, profile)

    query = select(NewsEvent).where(NewsEvent.is_active.is_(True))
    if impact is not None:
        query = query.where(NewsEvent.impact == impact.value)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(NewsEvent.title.ilike(pattern) | NewsEvent.summary.ilike(pattern))
    events = list((await session.execute(query)).scalars())

    pairs: list[tuple[FeedItem, NewsEvent]] = []
    for event in events:
        if category is not None and category not in (event.category_ids or []):
            continue
        if not include_tracked and event.id in tracked_ids:
            continue
        if not include_skipped and event.id in skipped_ids:
            continue
        match = match_event(event, categories, counterparties)
        pairs.append(
            (
                event_to_feed_item(event, match, is_tracked=event.id in tracked_ids),
                event,
            )
        )
    pairs.sort(key=lambda pair: (-pair[0].importance, -recency_key(pair[1]).timestamp()))
    total = len(pairs)
    return Page[FeedItem](
        items=[item for item, _ in pairs[offset : offset + limit]],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{event_id}", response_model=FeedItemDetail)
async def get_event(
    event_id: UUID,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> FeedItemDetail:
    event = await session.get(NewsEvent, event_id)
    if event is None or not event.is_active:
        raise HTTPException(status_code=404, detail="Новость не найдена")
    categories = await load_categories(session, profile)
    counterparties = await load_counterparties(session, profile)
    tracked_ids = await load_tracked_ids(session, profile)
    match = match_event(event, categories, counterparties)
    item = event_to_feed_item(event, match, is_tracked=event.id in tracked_ids, with_details=True)
    assert isinstance(item, FeedItemDetail)
    return item


@router.post("/{event_id}/track", response_model=TrackedItemOut)
async def track_event(
    event_id: UUID,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> TrackedItemOut:
    event = await session.get(NewsEvent, event_id)
    if event is None or not event.is_active:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    existing = (
        await session.execute(
            select(TrackedItem).where(
                TrackedItem.profile_id == profile.id,
                TrackedItem.event_id == event.id,
            )
        )
    ).scalar_one_or_none()
    categories = await load_categories(session, profile)
    counterparties = await load_counterparties(session, profile)
    match = match_event(event, categories, counterparties)

    if existing is None:
        report = await analyze_event(
            profile=profile,
            event=event,
            business_categories=categories,
            counterparties=counterparties,
            match_importance=match.importance,
            matched_counterparties=match.matched_counterparties,
        )
        existing = TrackedItem(
            profile_id=profile.id,
            event_id=event.id,
            status="active",
            report=report,
        )
        session.add(existing)
        await session.commit()
        await session.refresh(existing)

    feed_item = event_to_feed_item(event, match, is_tracked=True)
    return TrackedItemOut(
        id=existing.id,
        event_id=existing.event_id,
        status=existing.status,
        report=existing.report,
        created_at=existing.created_at,
        updated_at=existing.updated_at,
        event=feed_item,
    )


@router.post("/{event_id}/feedback")
async def submit_feedback(
    event_id: UUID,
    payload: FeedbackRequest,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    event = await session.get(NewsEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Новость не найдена")
    row = (
        await session.execute(
            select(Feedback).where(
                Feedback.profile_id == profile.id,
                Feedback.event_id == event.id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = Feedback(profile_id=profile.id, event_id=event.id, action=payload.action)
        session.add(row)
    else:
        row.action = payload.action
    if payload.action in {"skip", "not_relevant"}:
        tracked = (
            await session.execute(
                select(TrackedItem).where(
                    TrackedItem.profile_id == profile.id,
                    TrackedItem.event_id == event.id,
                )
            )
        ).scalar_one_or_none()
        if tracked is not None:
            await session.delete(tracked)
    await session.commit()
    return {"ok": True}
