from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from back.api.deps import get_current_profile
from back.config import get_settings
from back.db.models import BusinessProfile, EventQuestion, NewsEvent, TrackedItem
from back.db.session import get_session
from back.schemas.feed import (
    AgentReanalyzeRequest,
    TrackedEventOut,
    TrackedItemOut,
    TrackedListResponse,
    TrackedQuestionRequest,
)
from back.schemas.insights import QuestionOut, ScenarioSetOut
from back.services.agent import analyze_event
from back.services.feed import event_to_feed_item, match_event
from back.services.insights import (
    build_insight,
    question_from_row,
    question_status_code,
    scenarios,
    timeline_from_events,
)
from back.services.personalization import load_categories, load_counterparties

router = APIRouter(prefix="/tracked", tags=["tracked"])


def _event_ids(item: TrackedItem) -> list[UUID]:
    result: list[UUID] = []
    for raw in item.event_ids or []:
        try:
            result.append(UUID(str(raw)))
        except ValueError:
            continue
    if not result:
        result = [item.event_id]
    return result


async def _events(session: AsyncSession, item: TrackedItem) -> list[NewsEvent]:
    events: list[NewsEvent] = []
    for event_id in _event_ids(item):
        event = await session.get(NewsEvent, event_id)
        if event is not None:
            events.append(event)
    return events


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


def _questions(item: TrackedItem) -> list[QuestionOut]:
    result: list[QuestionOut] = []
    for index, raw in enumerate(item.questions or []):
        if not isinstance(raw, dict):
            continue
        text = str(raw.get("text") or "").strip()
        if not text:
            continue
        status = str(raw.get("status") or "Ждём")
        result.append(
            QuestionOut(
                id=str(raw.get("id") or f"q{index + 1}"),
                text=text,
                status=status,
                status_code=question_status_code(status),
                answer=raw.get("answer"),
                source=raw.get("source"),
                date=raw.get("date"),
                internal=bool(raw.get("internal")),
            )
        )
    return result


async def _out(
    session: AsyncSession,
    profile: BusinessProfile,
    item: TrackedItem,
    categories,
    counterparties,
) -> TrackedItemOut:
    events = await _events(session, item)
    latest = events[-1] if events else item.event
    match = match_event(latest, categories, counterparties)
    insight = build_insight(latest, profile, match, item.report)
    feed_item = event_to_feed_item(
        latest,
        match,
        is_tracked=True,
        profile=profile,
        report=item.report,
    )
    tracked_events = []
    for index, event in enumerate(events):
        event_match = match_event(event, categories, counterparties)
        tracked_events.append(
            TrackedEventOut(
                event_id=event.id,
                title=event.title,
                what_changed=item.what_changed if index == len(events) - 1 else None,
                importance=event_match.importance,
                impact=event.impact,
                impact_label=event_to_feed_item(event, event_match).impact_label,
                published_at=event.published_at,
            )
        )
    questions = _questions(item)
    event_ids = [event.id for event in events] or [latest.id]
    user_rows = list(
        (
            await session.execute(
                select(EventQuestion)
                .where(
                    EventQuestion.profile_id == profile.id,
                    EventQuestion.event_id.in_(event_ids),
                )
                .order_by(EventQuestion.created_at)
            )
        ).scalars()
    )
    user_questions = [question_from_row(row) for row in user_rows]
    if insight is not None:
        insight.open_questions = [*insight.open_questions, *user_questions]
        insight.questions_answered = sum(
            1 for question in insight.open_questions if question.status_code != "waiting"
        )
        insight.questions_waiting = sum(
            1 for question in insight.open_questions if question.status_code == "waiting"
        )
        points, index, total = timeline_from_events(events or [latest], latest.id)
        insight.timeline = points
        insight.timeline_current_index = index
        insight.timeline_total = total

    return TrackedItemOut(
        id=item.id,
        event_id=item.event_id,
        status="archived" if item.status == "archived" else "active",
        title=item.title or latest.title,
        what_changed=item.what_changed,
        conclusions_changed=item.conclusions_changed,
        questions=questions,
        report=item.report,
        analysis_pending=bool((item.report or {}).get("analysis_pending")),
        created_at=item.created_at,
        updated_at=item.updated_at,
        event=feed_item,
        events=tracked_events,
        insight=insight,
    )


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
    items = [await _out(session, profile, row, categories, counterparties) for row in rows]
    return TrackedListResponse(items=items, total=len(items))


@router.get("/{item_id}/scenarios", response_model=ScenarioSetOut)
async def get_tracked_scenarios(
    item_id: UUID,
    horizon: str = Query(default="12m", pattern="^(3m|6m|12m)$"),
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> ScenarioSetOut:
    row = await session.get(TrackedItem, item_id)
    if row is None or row.profile_id != profile.id:
        raise HTTPException(status_code=404, detail="Отслеживаемая новость не найдена")
    events = await _events(session, row)
    latest = events[-1] if events else row.event
    return scenarios(latest, profile, horizon, row.report)


@router.get("/{item_id}", response_model=TrackedItemOut)
async def get_tracked(
    item_id: UUID,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> TrackedItemOut:
    rows = await _load_tracked(session, profile, item_id)
    if not rows:
        raise HTTPException(status_code=404, detail="Отслеживаемая новость не найдена")
    categories = await load_categories(session, profile)
    counterparties = await load_counterparties(session, profile)
    return await _out(session, profile, rows[0], categories, counterparties)


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


@router.post("/{item_id}/archive", response_model=TrackedItemOut)
async def archive_tracked(
    item_id: UUID,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> TrackedItemOut:
    row = await session.get(TrackedItem, item_id)
    if row is None or row.profile_id != profile.id:
        raise HTTPException(status_code=404, detail="Отслеживаемая новость не найдена")
    row.status = "archived"
    await session.commit()
    await session.refresh(row)
    categories = await load_categories(session, profile)
    counterparties = await load_counterparties(session, profile)
    return await _out(session, profile, row, categories, counterparties)


@router.post("/{item_id}/resume", response_model=TrackedItemOut)
async def resume_tracked(
    item_id: UUID,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> TrackedItemOut:
    row = await session.get(TrackedItem, item_id)
    if row is None or row.profile_id != profile.id:
        raise HTTPException(status_code=404, detail="Отслеживаемая новость не найдена")
    row.status = "active"
    await session.commit()
    await session.refresh(row)
    categories = await load_categories(session, profile)
    counterparties = await load_counterparties(session, profile)
    return await _out(session, profile, row, categories, counterparties)


@router.post("/{item_id}/questions", response_model=TrackedItemOut)
async def add_question(
    item_id: UUID,
    payload: TrackedQuestionRequest,
    profile: BusinessProfile = Depends(get_current_profile),
    session: AsyncSession = Depends(get_session),
) -> TrackedItemOut:
    row = await session.get(TrackedItem, item_id)
    if row is None or row.profile_id != profile.id:
        raise HTTPException(status_code=404, detail="Отслеживаемая новость не найдена")
    questions = list(row.questions or [])
    questions.append(
        {
            "id": uuid4().hex,
            "text": payload.question.strip(),
            "status": "Ждём",
            "internal": False,
        }
    )
    row.questions = questions
    await session.commit()
    await session.refresh(row)
    categories = await load_categories(session, profile)
    counterparties = await load_counterparties(session, profile)
    return await _out(session, profile, row, categories, counterparties)


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
    events = await _events(session, row)
    event = events[-1] if events else await session.get(NewsEvent, row.event_id)
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
        use_llm=get_settings().llm_agent_enabled,
        events=events,
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
    return await _out(session, profile, row, categories, counterparties)
