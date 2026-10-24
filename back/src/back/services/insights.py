from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from back.core.constants import IMPACT_LABELS, Impact
from back.db.models import BusinessProfile, NewsEvent
from back.schemas.insights import (
    ActionOut,
    AgentStepOut,
    AlfaAnalyticsOut,
    AssumptionOut,
    ChatMessageOut,
    ImpactTileOut,
    InsightOut,
    ProductOut,
    QuestionOut,
    ScenarioOut,
    ScenarioSetOut,
    ScoreComponentOut,
    SourceComparisonOut,
    SourcePostOut,
    ThesisOut,
    TimelinePointOut,
)
from back.services.feed import MatchResult


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def format_money(value: float) -> str:
    sign = "+" if value > 0 else "−" if value < 0 else ""
    amount = abs(value)
    if amount >= 1_000_000_000:
        return f"{sign}{amount / 1_000_000_000:.2f} млрд ₽".replace(".", ",")
    if amount >= 1_000_000:
        return f"{sign}{amount / 1_000_000:.0f} млн ₽"
    if amount >= 1_000:
        return f"{sign}{amount / 1_000:.0f} тыс. ₽"
    return f"{sign}{amount:.0f} ₽"


def _impact_label(value: str) -> str:
    try:
        return IMPACT_LABELS[Impact(value)]
    except ValueError:
        return value


def _report_dict(report: dict[str, Any] | None) -> dict[str, Any]:
    return report if isinstance(report, dict) else {}


def source_posts(event: NewsEvent) -> list[SourcePostOut]:
    raw = event.source_posts or []
    result: list[SourcePostOut] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        published = item.get("time") or item.get("published_at") or event.published_at
        if isinstance(published, str):
            try:
                published = datetime.fromisoformat(published)
            except ValueError:
                published = event.published_at
        tone = str(item.get("tone") or "neutral")
        status = "confirmed" if tone == "official" else "single"
        result.append(
            SourcePostOut(
                name=str(item.get("name") or event.source_name),
                time=_aware(published),
                tone=tone,
                text=str(item.get("text") or event.summary),
                is_primary=bool(item.get("is_primary")) or index == 0,
                handle=item.get("handle"),
                url=item.get("url"),
                image_url=item.get("image_url"),
                status=status,
                status_label="Подтверждено" if status == "confirmed" else "Один канал",
            )
        )
    if result:
        return result
    return [
        SourcePostOut(
            name=event.source_name,
            time=_aware(event.published_at),
            tone="official",
            text=event.summary,
            is_primary=True,
            url=event.source_url,
            image_url=getattr(event, "image_url", None),
            status="confirmed",
            status_label="Подтверждено",
        )
    ]


def score_breakdown(
    event: NewsEvent, match: MatchResult, profile: BusinessProfile
) -> tuple[list[ScoreComponentOut], str, str]:
    scale = max(1, min(5, round(match.importance / 20)))
    directness = 1.0 if match.matched_counterparties else 0.8 if match.matched_categories else 0.6
    if match.matched_counterparties:
        directness = 1.0
    age_days = max(0, (datetime.now(UTC) - _aware(event.published_at)).days)
    urgency = 1.0 if age_days < 7 else 0.9 if age_days < 30 else 0.75 if age_days < 90 else 0.6
    novelty = 5 if match.matched_categories or match.matched_counterparties else 2

    matched_names = ", ".join(item.short_name for item in match.matched_categories) or "профиль"
    counterparties = (
        ", ".join(match.matched_counterparties) if match.matched_counterparties else "не найдены"
    )
    components = [
        ScoreComponentOut(
            key="scale",
            label="Масштаб для компании",
            value=scale,
            text=f"Влияние {match.importance}/100; совпадение: {matched_names}.",
        ),
        ScoreComponentOut(
            key="directness",
            label="Прямота",
            value=round(directness * 5),
            text=(
                "Новость напрямую касается компании."
                if directness == 1.0
                else "Влияние идёт через контрагента или отрасль."
            ),
        ),
        ScoreComponentOut(
            key="urgency",
            label="Срочность",
            value=round(urgency * 5),
            text=(
                f"Событию {age_days} дн.; эффект "
                f"{'уже действует' if age_days < 7 else 'ожидается'}."
            ),
        ),
        ScoreComponentOut(
            key="novelty",
            label="Новизна",
            value=novelty,
            text=f"Упоминания контрагентов: {counterparties}.",
        ),
    ]
    share = (
        f"{matched_names} · совпадение с профилем"
        if match.matched_categories
        else "прямой доли в профиле нет"
    )
    return components, match.match_reason, share


def _thesis_category(text: str) -> str:
    lower = text.lower()
    if any(word in lower for word in ("срок", "дат", "ноябр", "декабр", "год", "месяц")):
        return "Сроки"
    if any(word in lower for word in ("участ", "компан", "контрагент", "экспортёр")):
        return "Участники"
    if any(word in lower for word in ("причин", "цель", "из-за", "после")):
        return "Причины"
    if any(word in lower for word in ("оцен", "прогноз", "ожида", "может")):
        return "Оценка"
    return "Факт"


def _thesis_status(raw: str | None) -> str:
    text = (raw or "").lower()
    if "официаль" in text:
        return "Официально"
    if "несколь" in text or "канал" in text:
        return "Пишут несколько каналов"
    if "мнен" in text:
        return "Мнение"
    return "Пишет один канал"


def theses(event: NewsEvent) -> list[ThesisOut]:
    posts = source_posts(event)
    names = [item.name for item in posts[:3]]
    result: list[ThesisOut] = []
    for fact in event.facts or []:
        if isinstance(fact, dict):
            text = str(fact.get("text") or "")
            status_raw = fact.get("status")
        else:
            text = str(fact)
            status_raw = None
        if not text:
            continue
        result.append(
            ThesisOut(
                category=_thesis_category(text),
                text=text,
                status=_thesis_status(status_raw),
                sources=names[:2],
            )
        )
    if not result:
        result.append(
            ThesisOut(
                category="Факт",
                text=event.summary,
                status="Пишет один канал",
                sources=names[:1],
            )
        )
    return result


def comparison(event: NewsEvent) -> SourceComparisonOut:
    posts = source_posts(event)
    agree = [item.text[:140] for item in posts if item.tone == "official"][:2]
    single = [item.text[:140] for item in posts if not item.is_primary][:2]
    return SourceComparisonOut(agree=agree, differ=[], single=single)


def alfa_analytics(
    event: NewsEvent, profile: BusinessProfile, report: dict[str, Any] | None = None
) -> AlfaAnalyticsOut | None:
    raw = _report_dict(report).get("alfa")
    if not isinstance(raw, dict):
        return None
    text = str(raw.get("text") or "").strip()
    if not text:
        return None
    return AlfaAnalyticsOut(author=str(raw.get("author") or ""), text=text)


HORIZON_MONTHS = {"3m": 3, "6m": 6, "12m": 12}
HORIZON_LABELS = {"3m": "3 месяца", "6m": "6 месяцев", "12m": "12 месяцев"}


def _company_revenue(profile: BusinessProfile) -> float | None:
    if profile.company and profile.company.revenue:
        return float(profile.company.revenue)
    summary = profile.reporting_summary or {}
    for key in ("revenue", "income", "выручка"):
        value = summary.get(key)
        if isinstance(value, (int, float)) and value > 0:
            return float(value)
    return None


def _scenario_origins(report: dict[str, Any], names: list[str]) -> list[str | None]:
    origins = report.get("scenario_origins")
    per_scenario = report.get("scenarios")
    result: list[str | None] = []
    for index, name in enumerate(names):
        value: Any = None
        if isinstance(origins, list) and index < len(origins):
            value = origins[index]
        elif isinstance(origins, dict):
            value = origins.get(name, origins.get(str(index)))
        if value is None and isinstance(per_scenario, list):
            matched = next(
                (
                    item
                    for item in per_scenario
                    if isinstance(item, dict) and str(item.get("name") or "") == name
                ),
                None,
            )
            if matched is None and index < len(per_scenario):
                matched = per_scenario[index]
            if isinstance(matched, dict):
                value = matched.get("origin")
        result.append(str(value) if value else None)
    return result


def scenarios(
    event: NewsEvent,
    profile: BusinessProfile,
    horizon: str = "12m",
    report: dict[str, Any] | None = None,
) -> ScenarioSetOut:
    months = HORIZON_MONTHS.get(horizon, 12)
    revenue = _company_revenue(profile)
    match_impact = event.impact or "neutral"
    share = 0.02
    if match_impact == "opportunity":
        share = 0.015
    elif match_impact == "neutral":
        share = 0.005
    lever_label = {
        "risk": "Доля эффекта, которую удастся перенести в цену или бюджет",
        "opportunity": "Доля эффекта, которую удастся реализовать",
    }.get(event.impact, "Доля эффекта, которую удастся учесть в плане")
    if revenue is None:
        return ScenarioSetOut(
            horizon=horizon,
            horizon_label=HORIZON_LABELS.get(horizon, "12 месяцев"),
            lever_label=lever_label,
            lever_values=[],
            scenarios=[],
            assumptions=[],
            note="",
            needs_profile=["выручка компании из отчётности или профиля"],
            forecast_note=_report_dict(report).get("forecast_note"),
        )
    base_annual = revenue * share * (event.importance / 100)
    sign = -1.0 if event.impact in {"risk", "mixed"} else 1.0
    base = sign * base_annual * months / 12
    if sign < 0:
        pessimistic = base * 1.4
        optimistic = base * 0.55
    else:
        pessimistic = base * 0.55
        optimistic = base * 1.4
    names = ["Пессимистичный", "Базовый", "Оптимистичный"]
    lever_values = ["0%", "15%", "50%"]
    origins = _scenario_origins(_report_dict(report), names)
    effects = [pessimistic, base, optimistic]
    notes = [
        "Параметры события складываются против компании.",
        "Эффект распределяется пропорционально профилю компании.",
        "Часть эффекта компенсируется действиями компании.",
    ]
    probabilities = [30, 50, 20]
    formulas = [
        f"{format_money(base)} × {'1,4' if sign < 0 else '0,55'}",
        (
            f"{format_money(revenue)} × "
            f"{share:.1%} × {event.importance}/100 × {months}/12"
        ),
        f"{format_money(base)} × {'0,55' if sign < 0 else '1,4'}",
    ]
    scenario_list = [
        ScenarioOut(
            name=name,
            effect=round(effects[index], 2),
            effect_label=format_money(effects[index]),
            probability=probabilities[index],
            note=notes[index],
            formula=formulas[index],
            share=lever_values[index],
            origin=origins[index],
            is_base="базов" in name.lower(),
        )
        for index, name in enumerate(names)
    ]
    raw_assumptions = _report_dict(report).get("assumptions")
    assumptions: list[AssumptionOut] = []
    if isinstance(raw_assumptions, list):
        for index, item in enumerate(raw_assumptions):
            if not isinstance(item, dict) or not item.get("label"):
                continue
            assumptions.append(
                AssumptionOut(
                    key=str(item.get("key") or f"assumption-{index + 1}"),
                    label=str(item["label"]),
                    effect=str(item.get("effect") or ""),
                )
            )
    raw_needs = _report_dict(report).get("needs_profile")
    needs = [str(item) for item in raw_needs] if isinstance(raw_needs, list) else []
    if revenue is None and "выручка компании из отчётности или профиля" not in needs:
        needs.append("выручка компании из отчётности или профиля")
    forecast_note = _report_dict(report).get("forecast_note")
    scenario_note = _report_dict(report).get("scenario_note")
    return ScenarioSetOut(
        horizon=horizon,
        horizon_label=HORIZON_LABELS.get(horizon, "12 месяцев"),
        lever_label=lever_label,
        lever_values=lever_values,
        scenarios=scenario_list,
        assumptions=assumptions,
        note=str(scenario_note) if scenario_note else "",
        needs_profile=needs,
        forecast_note=str(forecast_note) if forecast_note else None,
    )


QUESTION_LABELS = {
    "waiting": "Ждём",
    "confirmed": "Подтвердилось",
    "refuted": "Опровергнуто",
    "answered": "Ответ получен",
}


def question_from_row(row: object) -> QuestionOut:
    status = str(getattr(row, "status", "waiting"))
    return QuestionOut(
        id=str(getattr(row, "id", "")),
        text=str(getattr(row, "text", "")),
        status=QUESTION_LABELS.get(status, status),
        status_code=status,
        answer=getattr(row, "answer", None),
        source=getattr(row, "source", None),
        date=getattr(row, "date", None),
    )


def question_status_code(label: str) -> str:
    normalized = label.strip().lower()
    if normalized.startswith("жд"):
        return "waiting"
    if normalized.startswith("подтверд"):
        return "confirmed"
    if normalized.startswith("опроверг"):
        return "refuted"
    return "answered"


def _parse_questions(raw: Any) -> list[QuestionOut]:
    if not isinstance(raw, list):
        return []
    result: list[QuestionOut] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        status = str(item.get("status") or "Ждём")
        result.append(
            QuestionOut(
                id=str(item.get("id") or f"q{index + 1}"),
                text=text,
                status=status,
                status_code=str(item.get("status_code") or question_status_code(status)),
                answer=item.get("answer"),
                source=item.get("source"),
                date=item.get("date"),
                internal=bool(item.get("internal")),
            )
        )
    return result


def open_questions(
    event: NewsEvent, profile: BusinessProfile, report: dict[str, Any] | None = None
) -> list[QuestionOut]:
    return _parse_questions(_report_dict(report).get("open_questions"))


def timeline_point(event: NewsEvent, current_id: object | None) -> TimelinePointOut:
    return TimelinePointOut(
        date=_aware(event.published_at).strftime("%d.%m"),
        text=event.title,
        importance=event.importance,
        is_current=event.id == current_id,
    )


def timeline(event: NewsEvent) -> list[TimelinePointOut]:
    return [timeline_point(event, event.id)]


def timeline_from_events(
    events: list[NewsEvent], current_id: object | None
) -> tuple[list[TimelinePointOut], int, int]:
    ordered = sorted(events, key=lambda item: _aware(item.published_at))
    points = [timeline_point(item, current_id) for item in ordered]
    index = next(
        (position for position, point in enumerate(points) if point.is_current), len(points) - 1
    )
    return points, max(index, 0), len(points)


def checklist(event: NewsEvent, report: dict[str, Any] | None = None) -> list[str]:
    raw = _report_dict(report).get("checklist")
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def actions(
    event: NewsEvent, profile: BusinessProfile, report: dict[str, Any] | None = None
) -> list[ActionOut]:
    raw = _report_dict(report).get("actions")
    if not isinstance(raw, list):
        return []
    result: list[ActionOut] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        deadline_label = item.get("deadline_label")
        description = item.get("description")
        action_id = item.get("id")
        result.append(
            ActionOut(
                id=str(action_id) if action_id else None,
                title=title,
                role=str(item.get("role") or profile.role_label or "Ответственный"),
                description=str(description) if description else None,
                deadline=str(item.get("deadline") or deadline_label or "7 дней"),
                deadline_label=str(deadline_label) if deadline_label else None,
                origin=str(item.get("origin") or "AI"),
                is_primary=bool(item.get("is_primary")),
            )
        )
    return result


def agent_log(event: NewsEvent, report: dict[str, Any] | None = None) -> list[AgentStepOut]:
    steps = _report_dict(report).get("agent_steps")
    if not isinstance(steps, list):
        return []
    return [
        AgentStepOut(
            type=str(item.get("type") or "Шаг"),
            text=str(item.get("text") or ""),
            is_correction=bool(item.get("is_correction")),
            at=str(item.get("at")) if item.get("at") else None,
        )
        for item in steps
        if isinstance(item, dict) and item.get("text")
    ]


def product(event: NewsEvent) -> ProductOut | None:
    categories = {int(item) for item in event.category_ids or []}
    if categories & {1, 23}:
        return ProductOut(
            name="Процентный своп",
            description="Фиксация ставки по части плавающего долга.",
            benefit="Ограничивает рост процентных расходов при высокой ставке.",
        )
    if categories & {2, 4}:
        return ProductOut(
            name="Валютный форвард",
            description="Фиксация курса по экспортной выручке.",
            benefit="Снижает потери при неблагоприятном движении курса.",
        )
    if categories & {20}:
        return ProductOut(
            name="Экспортный факторинг",
            description="Финансирование под отгрузки с отсрочкой платежа.",
            benefit="Освобождает оборотный капитал.",
        )
    return None


def chat(event: NewsEvent, report: dict[str, Any] | None = None) -> list[ChatMessageOut]:
    raw = _report_dict(report).get("chat")
    if not isinstance(raw, list):
        return []
    result: list[ChatMessageOut] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question") or "").strip()
        answer = str(item.get("answer") or "").strip()
        if not question or not answer:
            continue
        result.append(
            ChatMessageOut(
                question=question,
                answer=answer,
                origin=str(item.get("origin") or "AI"),
            )
        )
    return result


def impact_tiles(
    event: NewsEvent, report: dict[str, Any] | None = None
) -> list[ImpactTileOut]:
    """Tiles chosen by the agent in report["impact_tiles"], else derived from metrics 3+."""
    raw = _report_dict(report).get("impact_tiles")
    if isinstance(raw, list) and raw:
        parsed: list[ImpactTileOut] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            tile_type = item.get("type")
            label = str(item.get("label") or "").strip()
            if tile_type not in {"metric", "statement", "accent"} or not label:
                continue
            value = item.get("value")
            note = item.get("note")
            span = item.get("span")
            parsed.append(
                ImpactTileOut(
                    type=tile_type,
                    value=str(value) if value is not None else None,
                    label=label,
                    note=str(note) if note is not None else None,
                    span=span if span in {"half", "full"} else "half",
                )
            )
        if parsed:
            return parsed

    result: list[ImpactTileOut] = []
    for metric in (event.impact_metrics or [])[2:]:
        if not isinstance(metric, dict):
            continue
        label = str(metric.get("label") or "")
        value = metric.get("value")
        note = metric.get("note")
        result.append(
            ImpactTileOut(
                type="metric",
                value=str(value) if value is not None else None,
                label=label,
                note=str(note).replace("\n", " ") if note else None,
                span="half",
            )
        )
    return result


def build_insight(
    event: NewsEvent,
    profile: BusinessProfile,
    match: MatchResult,
    report: dict[str, Any] | None = None,
) -> InsightOut:
    components, score_why, impact_share = score_breakdown(event, match, profile)
    questions = open_questions(event, profile, report)
    points = timeline(event)
    finished_at = _report_dict(report).get("analysis_finished_at")
    return InsightOut(
        sources=source_posts(event),
        score_breakdown=components,
        score_why=score_why,
        impact_share=impact_share,
        comparison=comparison(event),
        theses=theses(event),
        alfa=alfa_analytics(event, profile, report),
        impact_tiles=impact_tiles(event, report),
        scenarios=scenarios(event, profile, report=report),
        open_questions=questions,
        timeline=points,
        checklist=checklist(event, report),
        actions=actions(event, profile, report),
        agent_log=agent_log(event, report),
        product=product(event),
        chat=chat(event, report),
        facts=event.facts or [],
        questions_answered=sum(1 for item in questions if item.status_code != "waiting"),
        questions_waiting=sum(1 for item in questions if item.status_code == "waiting"),
        timeline_total=len(points),
        timeline_current_index=0,
        analysis_finished_at=str(finished_at) if finished_at else None,
    )
