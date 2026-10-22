from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from back.core.constants import IMPACT_LABELS, Impact
from back.db.models import BusinessProfile, Company, Counterparty, Feedback, NewsEvent, TrackedItem
from back.schemas.search import (
    SearchCompanyOut,
    SearchHistoryItem,
    SearchHistoryResponse,
    SearchNewsOut,
    SearchResponse,
)
from back.services.feed import match_event
from back.services.personalization import load_categories, load_counterparties

HISTORY_LIMIT = 10


def _impact_label(value: str) -> str:
    try:
        return IMPACT_LABELS[Impact(value)]
    except ValueError:
        return value


def _initials(value: str) -> str:
    words = [word for word in value.replace("«", "").replace("»", "").split() if word]
    return "".join(word[0].upper() for word in words[:2]) or "К"


async def _company_rows(
    session: AsyncSession, profile: BusinessProfile, term: str
) -> tuple[list[SearchCompanyOut], int]:
    pattern = f"%{term}%"
    filters = or_(
        Company.uid.ilike(pattern),
        Company.city.ilike(pattern),
        Company.region.ilike(pattern),
        Company.main_okved_name.ilike(pattern),
    )
    total = (
        await session.execute(select(func.count()).select_from(Company).where(filters))
    ).scalar_one()
    rows = list(
        (
            await session.execute(
                select(Company)
                .where(filters)
                .order_by(Company.revenue.desc().nullslast(), Company.uid)
                .limit(10)
            )
        ).scalars()
    )
    counterparty_rows = list(
        (
            await session.execute(select(Counterparty).where(Counterparty.profile_id == profile.id))
        ).scalars()
    )
    roles = {row.company_uid: row for row in counterparty_rows if row.company_uid}
    result: list[SearchCompanyOut] = []
    seen: set[str] = set()
    if (
        profile.company is not None
        and term.lower()
        in (
            f"{profile.company.uid} {profile.company.main_okved_name or ''} "
            f"{profile.company.city or ''} {profile.company.region or ''}"
        ).lower()
    ):
        company = profile.company
        result.append(
            SearchCompanyOut(
                uid=company.uid,
                name=profile.business_name,
                role="Ваша компания",
                city=company.city,
                region=company.region,
                okved=company.main_okved_name,
                revenue=company.revenue,
                revenue_segment=company.revenue_segment,
                initials=_initials(profile.business_name),
            )
        )
        seen.add(company.uid)
    for row in rows:
        if row.uid in seen:
            continue
        counterparty = roles.get(row.uid)
        role = (
            "Поставщик"
            if counterparty and counterparty.direction == "supplier"
            else "Покупатель"
            if counterparty
            else "Компания из базы"
        )
        name = counterparty.display_name if counterparty else f"Компания {row.uid}"
        result.append(
            SearchCompanyOut(
                uid=row.uid,
                name=name,
                role=role,
                city=row.city,
                region=row.region,
                okved=row.main_okved_name,
                revenue=row.revenue,
                revenue_segment=row.revenue_segment,
                initials=_initials(name),
            )
        )
        seen.add(row.uid)
    return result, total


async def _news_rows(
    session: AsyncSession, profile: BusinessProfile, term: str
) -> tuple[list[SearchNewsOut], int]:
    categories = await load_categories(session, profile)
    counterparties = await load_counterparties(session, profile)
    pattern = f"%{term}%"
    query = select(NewsEvent).where(
        NewsEvent.is_active.is_(True),
        or_(NewsEvent.title.ilike(pattern), NewsEvent.summary.ilike(pattern)),
    )
    events = list((await session.execute(query)).scalars())
    feedback = {
        row.event_id: row.action
        for row in (
            await session.execute(select(Feedback).where(Feedback.profile_id == profile.id))
        ).scalars()
    }
    tracked = set(
        (
            await session.execute(
                select(TrackedItem.event_id).where(TrackedItem.profile_id == profile.id)
            )
        ).scalars()
    )
    rows: list[SearchNewsOut] = []
    for event in events:
        match = match_event(event, categories, counterparties)
        action = feedback.get(event.id)
        rows.append(
            SearchNewsOut(
                id=event.id,
                title=event.title,
                summary=event.summary,
                impact=event.impact,
                impact_label=_impact_label(event.impact),
                importance=match.importance,
                published_at=event.published_at,
                source_name=event.source_name,
                is_hidden=action in {"skip", "not_relevant"},
                is_tracked=event.id in tracked,
            )
        )
    rows.sort(key=lambda item: (-item.importance, -item.published_at.timestamp()))
    return rows[:30], len(rows)


def _history(profile: BusinessProfile) -> list[SearchHistoryItem]:
    items: list[SearchHistoryItem] = []
    for item in profile.search_history or []:
        if not isinstance(item, dict) or not item.get("query"):
            continue
        try:
            created = datetime.fromisoformat(str(item.get("created_at")))
        except ValueError:
            created = datetime.now(UTC)
        items.append(
            SearchHistoryItem(
                id=str(item.get("id") or uuid4()),
                query=str(item["query"]),
                created_at=created,
            )
        )
    return items


def search_history(profile: BusinessProfile) -> SearchHistoryResponse:
    return SearchHistoryResponse(items=_history(profile))


def remember_query(profile: BusinessProfile, query: str) -> None:
    term = query.strip()
    if len(term) < 2:
        return
    current = [
        item
        for item in (profile.search_history or [])
        if isinstance(item, dict) and item.get("query") != term
    ]
    current.insert(
        0,
        {
            "id": uuid4().hex,
            "query": term,
            "created_at": datetime.now(UTC).isoformat(),
        },
    )
    profile.search_history = current[:HISTORY_LIMIT]


def clear_history(profile: BusinessProfile) -> None:
    profile.search_history = []


def remove_history(profile: BusinessProfile, item_id: str) -> bool:
    current = profile.search_history or []
    filtered = [
        item for item in current if not (isinstance(item, dict) and str(item.get("id")) == item_id)
    ]
    profile.search_history = filtered
    return len(filtered) != len(current)


async def search(session: AsyncSession, profile: BusinessProfile, query: str) -> SearchResponse:
    term = (query or "").strip()
    if not term:
        return SearchResponse(query=term, companies=[], news=[], total_companies=0, total_news=0)
    companies, total_companies = await _company_rows(session, profile, term)
    news, total_news = await _news_rows(session, profile, term)
    remember_query(profile, term)
    await session.commit()
    return SearchResponse(
        query=term,
        companies=companies,
        news=news,
        total_companies=total_companies,
        total_news=total_news,
    )
