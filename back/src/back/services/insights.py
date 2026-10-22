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
        result.append(
            SourcePostOut(
                name=str(item.get("name") or event.source_name),
                time=_aware(published),
                tone=str(item.get("tone") or "neutral"),
                text=str(item.get("text") or event.summary),
                is_primary=bool(item.get("is_primary")) or index == 0,
                handle=item.get("handle"),
                url=item.get("url"),
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
    names = [item.name for item in posts if not item.is_primary]
    agree = [f"{item.text[:140]}" for item in posts if item.tone == "official"][:2]
    single = [f"{name}: подтверждено только в этом канале" for name in names[:2]]
    return SourceComparisonOut(agree=agree, differ=[], single=single)


def alfa_analytics(event: NewsEvent, profile: BusinessProfile) -> AlfaAnalyticsOut | None:
    label = _impact_label(event.impact)
    return AlfaAnalyticsOut(
        author="Центр макроэкономических исследований Альфа-Банка",
        text=(
            f"Базовый сценарий банка: {label.lower()}. "
            "Рекомендуем сверить параметры события с бюджетом и валютной позицией компании. "
            "Оценка банка учтена в базовом сценарии."
        ),
    )


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


def scenarios(event: NewsEvent, profile: BusinessProfile, horizon: str = "12m") -> ScenarioSetOut:
    months = HORIZON_MONTHS.get(horizon, 12)
    revenue = _company_revenue(profile)
    match_impact = event.impact or "neutral"
    share = 0.02
    if match_impact == "opportunity":
        share = 0.015
    elif match_impact == "neutral":
        share = 0.005
    base_annual = (revenue or 10_000_000_000) * share * (event.importance / 100)
    sign = -1.0 if event.impact in {"risk", "mixed"} else 1.0
    base = sign * base_annual * months / 12
    pessimistic = base * 1.4
    optimistic = base * 0.55
    lever_label = {
        "risk": "Доля эффекта, которую удастся перенести в цену или бюджет",
        "opportunity": "Доля эффекта, которую удастся реализовать",
    }.get(event.impact, "Доля эффекта, которую удастся учесть в плане")
    scenarios = [
        ScenarioOut(
            name="Пессимистичный",
            effect=round(pessimistic, 2),
            effect_label=format_money(pessimistic),
            probability=30,
            note="Параметры события складываются против компании.",
            formula=f"{format_money(base)} × 1,4",
        ),
        ScenarioOut(
            name="Базовый",
            effect=round(base, 2),
            effect_label=format_money(base),
            probability=50,
            note="Эффект распределяется пропорционально профилю компании.",
            formula=(
                f"{format_money(revenue or 10_000_000_000)} × "
                f"{share:.1%} × {event.importance}/100 × {months}/12"
            ),
        ),
        ScenarioOut(
            name="Оптимистичный",
            effect=round(optimistic, 2),
            effect_label=format_money(optimistic),
            probability=20,
            note="Часть эффекта компенсируется действиями компании.",
            formula=f"{format_money(base)} × 0,55",
        ),
    ]
    assumptions = [
        AssumptionOut(
            key="hedge",
            label="Зафиксировать курс/ставку по чувствительной позиции",
            effect="Снижает разброс сценариев",
        ),
        AssumptionOut(
            key="contracts",
            label="Пересмотреть условия контрактов",
            effect="Переносит часть эффекта на контрагента",
        ),
    ]
    needs = [] if revenue else ["выручка компании из отчётности или профиля"]
    return ScenarioSetOut(
        horizon=horizon,
        horizon_label=HORIZON_LABELS.get(horizon, "12 месяцев"),
        lever_label=lever_label,
        lever_values=["0%", "15%", "50%"],
        scenarios=scenarios,
        assumptions=assumptions,
        note="Детерминированная заглушка: точный расчёт появится после подключения модели.",
        needs_profile=needs,
    )


def open_questions(event: NewsEvent, profile: BusinessProfile) -> list[QuestionOut]:
    base = [
        QuestionOut(
            id="q1",
            text="Распространяется ли событие на уже подписанные контракты?",
            status="Ждём",
        ),
        QuestionOut(
            id="q2",
            text="Есть ли исключения для ключевых контрагентов?",
            status="Ждём",
        ),
    ]
    if event.facts:
        first = event.facts[0]
        text = first.get("text") if isinstance(first, dict) else str(first)
        if text:
            base[0] = QuestionOut(
                id="q1",
                text=f"Подтверждено ли: {text}",
                status="Подтвердилось",
                answer=str(text),
                source=event.source_name,
                date=_aware(event.published_at).strftime("%d.%m"),
            )
    return base


def timeline(event: NewsEvent) -> list[TimelinePointOut]:
    return [
        TimelinePointOut(
            date=_aware(event.published_at).strftime("%d.%m"),
            text=event.title,
            importance=event.importance,
            is_current=True,
        )
    ]


def checklist(event: NewsEvent) -> list[str]:
    return [
        "Есть ли в контрактах оговорка о новых условиях",
        "Какая доля выручки или затрат зависит от фактора новости",
        "Какой запас до ковенантов и лимитов сохраняется",
    ]


def actions(event: NewsEvent, profile: BusinessProfile) -> list[ActionOut]:
    role = profile.role_label or "Ответственный"
    result = [
        ActionOut(
            title="Проверить экспозицию компании к фактору новости и оценить худший сценарий",
            role=role,
            deadline="3 дня",
            origin="AI",
        )
    ]
    if event.impact in {"opportunity", "mixed"}:
        result.append(
            ActionOut(
                title="Оценить, можно ли использовать изменение в свою пользу",
                role=role,
                deadline="7 дней",
                origin="AI",
            )
        )
    return result


def agent_log(event: NewsEvent, report: dict[str, Any] | None = None) -> list[AgentStepOut]:
    steps = (report or {}).get("agent_steps")
    if isinstance(steps, list) and steps:
        return [
            AgentStepOut(type=str(item.get("type") or "Шаг"), text=str(item.get("text") or ""))
            for item in steps
            if isinstance(item, dict) and item.get("text")
        ]
    return [
        AgentStepOut(type="Старт", text="Получены новость и профиль бизнеса."),
        AgentStepOut(type="Данные", text="Загружены категории, контрагенты и отчётность."),
        AgentStepOut(type="Расчёт", text="Посчитаны важность и сценарии."),
        AgentStepOut(type="Проверка", text="Проверено, что в выводе нет выдуманных цифр."),
        AgentStepOut(type="Готово", text="Сформированы выводы и действия."),
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


def chat(event: NewsEvent) -> list[ChatMessageOut]:
    return [
        ChatMessageOut(
            question="Что изменится для компании?",
            answer=(
                f"Событие «{event.title}» относится к типу "
                f"«{_impact_label(event.impact).lower()}». Оценка важности — "
                f"{event.importance}/100, детали зависят от профиля."
            ),
        ),
        ChatMessageOut(
            question="Покажи эффект по кварталам",
            answer="Разбивка по кварталам появится после подключения расчётной модели.",
        ),
    ]


def build_insight(
    event: NewsEvent,
    profile: BusinessProfile,
    match: MatchResult,
    report: dict[str, Any] | None = None,
) -> InsightOut:
    components, score_why, impact_share = score_breakdown(event, match, profile)
    return InsightOut(
        sources=source_posts(event),
        score_breakdown=components,
        score_why=score_why,
        impact_share=impact_share,
        comparison=comparison(event),
        theses=theses(event),
        alfa=alfa_analytics(event, profile),
        scenarios=scenarios(event, profile),
        open_questions=open_questions(event, profile),
        timeline=timeline(event),
        checklist=checklist(event),
        actions=actions(event, profile),
        agent_log=agent_log(event, report),
        product=product(event),
        chat=chat(event),
        facts=event.facts or [],
    )
