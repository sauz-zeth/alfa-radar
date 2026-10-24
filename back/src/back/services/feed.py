from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from back.core.categories import CATEGORY_BY_ID
from back.core.constants import IMPACT_LABELS, PROGNOSIS_NOTE, Impact
from back.db.models import BusinessCategory, BusinessProfile, Counterparty, NewsEvent
from back.schemas.feed import CategoryBrief, FeedItem, FeedItemDetail
from back.schemas.insights import ImpactMetricOut


@dataclass
class MatchResult:
    importance: int
    matched_categories: list[CategoryBrief]
    matched_counterparties: list[str]
    match_reason: str


def _category_brief(category_id: int) -> CategoryBrief | None:
    category = CATEGORY_BY_ID.get(category_id)
    if not category:
        return None
    return CategoryBrief(id=category.id, name=category.name, short_name=category.short_name)


def match_event(
    event: NewsEvent,
    business_categories: list[BusinessCategory],
    counterparties: list[Counterparty],
) -> MatchResult:
    weights = {item.category_id: item.weight for item in business_categories}
    matched: list[CategoryBrief] = []
    max_weight = 0.0
    for category_id in event.category_ids or []:
        weight = weights.get(int(category_id), 0.0)
        if weight > 0:
            brief = _category_brief(int(category_id))
            if brief:
                matched.append(brief)
                max_weight = max(max_weight, weight)

    matched_counterparties: list[str] = []
    mentioned = set(event.mentioned_company_uids or [])
    if mentioned:
        for counterparty in counterparties:
            if counterparty.company_uid in mentioned:
                matched_counterparties.append(counterparty.display_name)

    importance = event.importance
    if max_weight > 0:
        importance = round(event.importance * (0.65 + 0.35 * max_weight))
    else:
        importance = round(event.importance * 0.6)
    if matched_counterparties:
        importance = min(100, importance + 15)

    if matched_counterparties and matched:
        reason = "Совпали категории профиля и важный контрагент."
    elif matched_counterparties:
        reason = "Новость упоминает важного контрагента."
    elif matched:
        reason = "Совпали категории влияния из профиля бизнеса."
    else:
        reason = "Фоновая новость: прямое совпадение с профилем не найдено."

    return MatchResult(
        importance=max(1, min(100, importance)),
        matched_categories=matched,
        matched_counterparties=sorted(set(matched_counterparties)),
        match_reason=reason,
    )


def _impact_label(impact: str) -> str:
    try:
        return IMPACT_LABELS[Impact(impact)]
    except ValueError:
        return impact


def _all_categories(event: NewsEvent) -> list[CategoryBrief]:
    result: list[CategoryBrief] = []
    for category_id in event.category_ids or []:
        brief = _category_brief(int(category_id))
        if brief:
            result.append(brief)
    return result


METRIC_LABELS = ("EBITDA в год", "Экспорт под пошлиной", "Доля эффекта")


def _impact_metrics(event: NewsEvent) -> list[ImpactMetricOut]:
    result: list[ImpactMetricOut] = []
    for index, raw in enumerate(event.impact_metrics or []):
        if not isinstance(raw, dict):
            continue
        note = str(raw.get("note") or "")
        fallback = note.split("\n")[0].strip() or METRIC_LABELS[min(index, len(METRIC_LABELS) - 1)]
        label = str(raw.get("label") or fallback)
        tone = raw.get("tone")
        result.append(
            ImpactMetricOut(
                key=raw.get("key"),
                label=label,
                value=str(raw.get("value") or "—"),
                previous_value=raw.get("previous_value"),
                unit=raw.get("unit"),
                note=note.replace("\n", " "),
                tone=tone if tone in {"negative", "positive"} else None,
            )
        )
    return result


def event_to_feed_item(
    event: NewsEvent,
    match: MatchResult,
    *,
    is_tracked: bool = False,
    with_details: bool = False,
    profile: BusinessProfile | None = None,
    is_liked: bool = False,
    likes: int = 0,
    report: dict[str, Any] | None = None,
) -> FeedItem:
    # Local import avoids a cycle: insights imports MatchResult from this module.
    from back.services.insights import build_insight

    insight = build_insight(event, profile, match, report) if profile is not None else None
    payload: dict[str, Any] = {
        "id": event.id,
        "title": event.title,
        "summary": event.summary,
        "what_it_means": event.what_it_means,
        "source_name": event.source_name,
        "source_url": event.source_url,
        "published_at": event.published_at,
        "impact": event.impact,
        "impact_label": _impact_label(event.impact),
        "importance": match.importance,
        "categories": _all_categories(event),
        "matched_categories": match.matched_categories,
        "matched_counterparties": match.matched_counterparties,
        "match_reason": match.match_reason,
        "is_tracked": is_tracked,
        "is_liked": is_liked,
        "likes": likes,
        "source_count": len(insight.sources) if insight else len(event.source_posts or []) or 1,
        "sources": insight.sources if insight else [],
        "facts": event.facts or [],
        "impact_metrics": _impact_metrics(event),
        "score_breakdown": insight.score_breakdown if insight else [],
        "score_why": insight.score_why if insight else match.match_reason,
        "impact_share": insight.impact_share if insight else "",
        "is_important_mention": bool(match.matched_counterparties),
        "chain_key": event.chain_key,
        "update_label": event.update_label,
        "changed_at": event.published_at if event.update_label else None,
        "conclusions_changed": bool(event.update_label),
        "prognosis_note": PROGNOSIS_NOTE,
        "detail_note": f"(!) {PROGNOSIS_NOTE}",
    }
    if with_details:
        if insight is not None:
            payload.update(insight.model_dump())
        return FeedItemDetail(**payload)
    return FeedItem(**payload)


def recency_key(event: NewsEvent) -> datetime:
    published_at = event.published_at
    if published_at.tzinfo is None:
        return published_at.replace(tzinfo=UTC)
    return published_at
