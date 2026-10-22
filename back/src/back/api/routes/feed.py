from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from back.api.deps import get_current_profile
from back.core.constants import Impact
from back.db.models import BusinessProfile, EventLike, Feedback, NewsEvent, TrackedItem
from back.db.session import get_session
from back.schemas.common import Page
from back.schemas.feed import (
    FeedbackRequest,
    FeedItem,
    FeedItemDetail,
    HiddenItem,
    HiddenResponse,
    HiddenTab,
    LikeResponse,
    TrackedEventOut,
    TrackedItemOut,
)
from back.schemas.insights import ScenarioSetOut
from back.services.agent import analyze_event
from back.services.feed import MatchResult, event_to_feed_item, match_event, recency_key
from back.services.insights import build_insight, scenarios
from back.services.personalization import (
    load_categories,
    load_counterparties,
    load_skipped_ids,
    load_tracked_ids,
)

router = APIRouter(prefix="/feed", tags=["feed"])

HIDDEN_TABS = {
    "stale": "Пробыли в ленте больше 3 дней без решения — событие уже потеряло актуальность.",
    "weak": ("Важность ниже 30 из 100 — событие слабо влияет на показатели из профиля компании."),
    "skipped": "Новости, которые вы смахнули влево. Вернуть можно, пока они не удалены.",
}
HIDDEN_LABELS = {"stale": "Устаревшие", "weak": "Слабое влияние", "skipped": "Пропущенные"}
STALE_AFTER = timedelta(days=3)
HIDDEN_TTL = 7


async def _like_maps(
    session: AsyncSession, profile: BusinessProfile, event_ids: list[UUID]
) -> tuple[dict[UUID, int], set[UUID]]:
    if not event_ids:
        return {}, set()
    counts = dict(
        (
            await session.execute(
                select(EventLike.event_id, func.count())
                .where(EventLike.event_id.in_(event_ids))
                .group_by(EventLike.event_id)
            )
        ).all()
    )
    liked = set(
        (
            await session.execute(
                select(EventLike.event_id).where(
                    EventLike.profile_id == profile.id,
                    EventLike.event_id.in_(event_ids),
                )
            )
        ).scalars()
    )
    return counts, liked


def _age_days(event: NewsEvent) -> int:
    published = event.published_at
    if published.tzinfo is None:
        published = published.replace(tzinfo=UTC)
    return max(0, (datetime.now(UTC) - published).days)


def _is_stale(event: NewsEvent) -> bool:
    published = (
        event.published_at.replace(tzinfo=UTC)
        if event.published_at.tzinfo is None
        else event.published_at
    )
    return datetime.now(UTC) - published >= STALE_AFTER


def _hidden_item(
    event: NewsEvent,
    match: MatchResult,
    age: int,
    *,
    reason: str,
    action: str,
) -> HiddenItem:
    return HiddenItem(
        id=event.id,
        title=event.title,
        impact=event.impact,
        impact_label=event_to_feed_item(event, match).impact_label,
        importance=match.importance,
        published_at=event.published_at,
        source_name=event.source_name,
        age_days=age,
        expires_in_days=max(0, HIDDEN_TTL - age),
        reason=reason,
        action=action,
    )


async def _hidden_rows(
    session: AsyncSession,
    profile: BusinessProfile,
    tab: str,
    categories,
    counterparties,
    tracked_ids: set[UUID],
) -> tuple[list[HiddenItem], int, int, int]:
    feedback_rows = list(
        (await session.execute(select(Feedback).where(Feedback.profile_id == profile.id))).scalars()
    )
    feedback_by_event = {row.event_id: row for row in feedback_rows}
    events = list(
        (await session.execute(select(NewsEvent).where(NewsEvent.is_active.is_(True)))).scalars()
    )
    stale: list[HiddenItem] = []
    weak: list[HiddenItem] = []
    skipped: list[HiddenItem] = []
    for event in events:
        row = feedback_by_event.get(event.id)
        action = row.action if row else None
        match = match_event(event, categories, counterparties)
        age = _age_days(event)
        if age > HIDDEN_TTL:
            continue
        if event.id in tracked_ids or action == "important":
            continue
        if action in {"skip", "not_relevant"}:
            skipped.append(
                _hidden_item(
                    event,
                    match,
                    age,
                    reason=(row.reason if row and row.reason else "Без указания причины"),
                    action="restore",
                )
            )
            continue
        if match.importance < 30:
            weak.append(
                _hidden_item(
                    event,
                    match,
                    age,
                    reason="Важность ниже 30 из 100",
                    action="important",
                )
            )
            continue
        if _is_stale(event):
            stale.append(
                _hidden_item(
                    event,
                    match,
                    age,
                    reason=f"Было в ленте {age} дн.",
                    action="restore",
                )
            )
    selected = {"stale": stale, "weak": weak, "skipped": skipped}[tab]
    selected.sort(key=lambda item: (item.importance, item.published_at), reverse=True)
    return selected, len(stale), len(weak), len(skipped)


@router.get("", response_model=Page[FeedItem])
async def get_feed(
    impact: Impact | None = None,
    category: int | None = Query(default=None, ge=1, le=30),
    q: str | None = Query(default=None, max_length=200),
    include_tracked: bool = False,
    include_skipped: bool = False,
    include_hidden: bool = False,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> Page[FeedItem]:
    categories = await load_categories(session, profile)
    counterparties = await load_counterparties(session, profile)
    tracked_ids = await load_tracked_ids(session, profile)
    skipped_ids = await load_skipped_ids(session, profile)
    important_ids = set(
        (
            await session.execute(
                select(Feedback.event_id).where(
                    Feedback.profile_id == profile.id,
                    Feedback.action == "important",
                )
            )
        ).scalars()
    )

    query = select(NewsEvent).where(NewsEvent.is_active.is_(True))
    if impact is not None:
        query = query.where(NewsEvent.impact == impact.value)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(NewsEvent.title.ilike(pattern) | NewsEvent.summary.ilike(pattern))
    events = list((await session.execute(query)).scalars())

    selected_events: list[tuple[NewsEvent, MatchResult]] = []
    for event in events:
        if category is not None and category not in (event.category_ids or []):
            continue
        if not include_tracked and event.id in tracked_ids:
            continue
        if not include_skipped and event.id in skipped_ids:
            continue
        match = match_event(event, categories, counterparties)
        if (
            not include_hidden
            and event.id not in important_ids
            and (match.importance < 30 or _is_stale(event))
        ):
            continue
        selected_events.append((event, match))

    like_counts, liked_ids = await _like_maps(
        session, profile, [event.id for event, _ in selected_events]
    )
    enriched = [
        (
            event_to_feed_item(
                event,
                match,
                is_tracked=event.id in tracked_ids,
                profile=profile,
                is_liked=event.id in liked_ids,
                likes=like_counts.get(event.id, 0),
            ),
            event,
        )
        for event, match in selected_events
    ]
    enriched.sort(key=lambda pair: (-pair[0].importance, -recency_key(pair[1]).timestamp()))
    total = len(enriched)
    return Page[FeedItem](
        items=[item for item, _ in enriched[offset : offset + limit]],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/hidden", response_model=HiddenResponse)
async def get_hidden(
    tab: str = Query(default="stale", pattern="^(stale|weak|skipped)$"),
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> HiddenResponse:
    categories = await load_categories(session, profile)
    counterparties = await load_counterparties(session, profile)
    tracked_ids = await load_tracked_ids(session, profile)
    selected, stale_count, weak_count, skipped_count = await _hidden_rows(
        session, profile, tab, categories, counterparties, tracked_ids
    )
    tabs = [
        HiddenTab(key="stale", label=HIDDEN_LABELS["stale"], count=stale_count),
        HiddenTab(key="weak", label=HIDDEN_LABELS["weak"], count=weak_count),
        HiddenTab(key="skipped", label=HIDDEN_LABELS["skipped"], count=skipped_count),
    ]
    return HiddenResponse(
        tab=tab,
        description=HIDDEN_TABS[tab],
        total=len(selected),
        tabs=tabs,
        items=selected,
    )


@router.post("/{event_id}/restore")
async def restore_hidden(
    event_id: UUID,
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
                Feedback.event_id == event_id,
            )
        )
    ).scalar_one_or_none()
    if row is not None and row.action in {"skip", "not_relevant"}:
        await session.delete(row)
    else:
        if row is None:
            row = Feedback(profile_id=profile.id, event_id=event_id, action="important")
            session.add(row)
        else:
            row.action = "important"
            row.reason = None
    await session.commit()
    return {"ok": True}


@router.post("/{event_id}/like", response_model=LikeResponse)
async def toggle_like(
    event_id: UUID,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> LikeResponse:
    event = await session.get(NewsEvent, event_id)
    if event is None or not event.is_active:
        raise HTTPException(status_code=404, detail="Новость не найдена")
    row = (
        await session.execute(
            select(EventLike).where(
                EventLike.profile_id == profile.id,
                EventLike.event_id == event_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        session.add(EventLike(profile_id=profile.id, event_id=event_id))
        liked = True
    else:
        await session.delete(row)
        liked = False
    await session.commit()
    count = (
        await session.execute(
            select(func.count()).select_from(EventLike).where(EventLike.event_id == event_id)
        )
    ).scalar_one()
    return LikeResponse(liked=liked, likes=count)


@router.get("/{event_id}/scenarios", response_model=ScenarioSetOut)
async def get_scenarios(
    event_id: UUID,
    horizon: str = Query(default="12m", pattern="^(3m|6m|12m)$"),
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> ScenarioSetOut:
    event = await session.get(NewsEvent, event_id)
    if event is None or not event.is_active:
        raise HTTPException(status_code=404, detail="Новость не найдена")
    return scenarios(event, profile, horizon)


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
    counts, liked_ids = await _like_maps(session, profile, [event.id])
    item = event_to_feed_item(
        event,
        match,
        is_tracked=event.id in tracked_ids,
        with_details=True,
        profile=profile,
        is_liked=event.id in liked_ids,
        likes=counts.get(event.id, 0),
    )
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
            title=event.title,
            event_ids=[str(event.id)],
            report=report,
        )
        session.add(existing)
        await session.commit()
        await session.refresh(existing)

    feed_item = event_to_feed_item(
        event, match, is_tracked=True, profile=profile, report=existing.report
    )
    return TrackedItemOut(
        id=existing.id,
        event_id=existing.event_id,
        status=existing.status,
        title=existing.title,
        what_changed=existing.what_changed,
        conclusions_changed=existing.conclusions_changed,
        report=existing.report,
        created_at=existing.created_at,
        updated_at=existing.updated_at,
        event=feed_item,
        events=[
            TrackedEventOut(
                event_id=event.id,
                title=event.title,
                importance=match.importance,
                impact=event.impact,
                impact_label=feed_item.impact_label,
                published_at=event.published_at,
            )
        ],
        insight=build_insight(event, profile, match, existing.report),
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
        row = Feedback(
            profile_id=profile.id, event_id=event.id, action=payload.action, reason=payload.reason
        )
        session.add(row)
    else:
        row.action = payload.action
        row.reason = payload.reason
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
