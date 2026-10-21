import contextlib
import logging
from typing import Any

from back.core.constants import (
    IMPACT_LABELS,
    PROGNOSIS_NOTE,
    Impact,
    Role,
)
from back.db.models import BusinessCategory, BusinessProfile, Counterparty, NewsEvent
from back.llm.factory import get_llm
from back.llm.prompts import AGENT_SYSTEM, agent_prompt
from back.services.counterparties import counterparty_context
from back.services.reporting import reporting_context

logger = logging.getLogger(__name__)

ROLE_FOCUS: dict[Role, str] = {
    Role.OWNER: "стоимость бизнеса, стратегические риски и решения собственника",
    Role.CEO: "операционные последствия, ответственность и приоритеты управления",
    Role.CFO: "финансовый результат, ликвидность и долговая нагрузка",
    Role.CHIEF_ACCOUNTANT: "налоги, бухгалтерский учёт, отчётность и сроки",
    Role.TREASURER: "ликвидность, платежи, кассовый план и валютные позиции",
    Role.C_LEVEL: "кросс-функциональные последствия для вашего направления",
    Role.OTHER_DECISION_MAKER: "практические последствия для вашей зоны ответственности",
}

ROLE_FOCUS_FALLBACK = "последствия для вашей роли и зоны ответственности"


def _role_focus(profile: BusinessProfile) -> str:
    try:
        return ROLE_FOCUS[Role(profile.role)] if profile.role else ROLE_FOCUS_FALLBACK
    except ValueError:
        return ROLE_FOCUS_FALLBACK


def _profile_context(
    profile: BusinessProfile,
    business_categories: list[BusinessCategory],
    counterparties: list[Counterparty],
) -> dict[str, Any]:
    company = profile.company
    return {
        "business_name": profile.business_name,
        "entrepreneur_name": profile.entrepreneur_name,
        "role": profile.role,
        "role_label": profile.role_label,
        "company": {
            "uid": company.uid if company else None,
            "okved": company.main_okved_name if company else None,
            "revenue": company.revenue if company else None,
            "revenue_segment": company.revenue_segment if company else None,
            "city": company.city if company else None,
            "region": company.region if company else None,
            "fts_country": company.fts_country_name if company else None,
        },
        "categories": [
            {
                "category_id": item.category_id,
                "name": item.category.name if item.category else str(item.category_id),
                "weight": item.weight,
                "rationale": item.rationale,
            }
            for item in business_categories
            if item.weight > 0
        ],
        "counterparties": counterparty_context(counterparties),
        "reporting": reporting_context(profile),
    }


def _event_context(event: NewsEvent) -> dict[str, Any]:
    return {
        "title": event.title,
        "summary": event.summary,
        "what_it_means": event.what_it_means,
        "impact": event.impact,
        "importance": event.importance,
        "category_ids": event.category_ids,
        "source": event.source_name,
        "facts": event.facts,
    }


def _actions(role_focus: str, impact: str) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    if impact in {Impact.RISK.value, Impact.MIXED.value}:
        actions.append(
            {
                "title": (
                    "Проверить экспозицию компании к фактору новости и оценить худший сценарий"
                ),
                "role": "Финансовый директор",
                "deadline": "3 дня",
                "origin": "AI",
            }
        )
    if impact in {Impact.OPPORTUNITY.value, Impact.MIXED.value}:
        actions.append(
            {
                "title": (
                    "Оценить, можно ли использовать изменение в свою пользу, и подготовить расчёт"
                ),
                "role": "Финансовый директор",
                "deadline": "7 дней",
                "origin": "AI",
            }
        )
    if role_focus.startswith("налоги"):
        actions.append(
            {
                "title": "Проверить налоговые и учётные последствия, сроки отчётности",
                "role": "Главный бухгалтер",
                "deadline": "5 дней",
                "origin": "AI",
            }
        )
    elif role_focus.startswith("ликвидность"):
        actions.append(
            {
                "title": "Обновить кассовый план и валютные позиции с учётом события",
                "role": "Руководитель казначейства",
                "deadline": "3 дня",
                "origin": "AI",
            }
        )
    actions.append(
        {
            "title": "Вернуться к разбору через неделю и проверить, подтвердился ли прогноз",
            "role": "Ответственный по новости",
            "deadline": "7 дней",
            "origin": "AI",
        }
    )
    return actions


def fallback_report(
    profile: BusinessProfile,
    event: NewsEvent,
    match_importance: int,
    matched_counterparties: list[str],
    has_reporting: bool,
) -> dict[str, Any]:
    role_focus = _role_focus(profile)
    impact = event.impact if event.impact in {item.value for item in Impact} else "neutral"
    impact_label = IMPACT_LABELS[Impact(impact)]
    counterparty_note = (
        f" В новости упоминаются контрагенты: {', '.join(matched_counterparties)}."
        if matched_counterparties
        else ""
    )
    reporting_note = (
        " Учтена выжимка из загруженной отчётности, поэтому прогноз может отличаться от ленты."
        if has_reporting
        else " Отчётность не загружена, поэтому прогноз основан только на профиле и новости."
    )
    what_happened = [str(fact.get("text") or fact) for fact in (event.facts or []) if fact] or [
        event.summary
    ]

    risks: list[str] = []
    opportunities: list[str] = []
    if impact in {Impact.RISK.value, Impact.MIXED.value}:
        risks.append(
            "Фактор новости может увеличить расходы или снизить выручку "
            "в вашей зоне ответственности."
        )
    if impact in {Impact.OPPORTUNITY.value, Impact.MIXED.value}:
        opportunities.append(
            "Изменение может открыть окно для пересмотра условий, экономии или роста выручки."
        )

    return {
        "what_happened": what_happened,
        "why_important": (
            f"Для роли «{profile.role_label or 'пользователь'}» событие важно через {role_focus}."
            f"{counterparty_note}{reporting_note}"
        ),
        "impact": impact,
        "impact_label": impact_label,
        "importance": match_importance,
        "prognosis": (
            f"Базовый прогноз: {impact_label.lower()}. Влияние оценено на "
            f"{match_importance}/100; при детальном разборе и загрузке отчётности "
            "прогноз может уточниться."
        ),
        "risks": risks,
        "opportunities": opportunities,
        "role_focus": role_focus,
        "actions": _actions(role_focus, impact),
        "agent_steps": [
            {"type": "Старт", "text": "Получены новость и профиль бизнеса."},
            {"type": "Данные", "text": "Загружены роль, категории, контрагенты и отчётность."},
            {
                "type": "Расчёт",
                "text": "Оценена важность и тип влияния (риск/возможность/смешанное).",
            },
            {"type": "Проверка", "text": "Проверено, что в выводе нет цифр, которых нет в данных."},
            {"type": "Готово", "text": "Сформированы выводы и действия."},
        ],
        "reporting_used": has_reporting,
        "prognosis_note": PROGNOSIS_NOTE,
    }


def _merge_report(fallback: dict[str, Any], llm_result: dict[str, Any]) -> dict[str, Any]:
    result = dict(fallback)
    for key in (
        "why_important",
        "prognosis",
        "role_focus",
    ):
        value = llm_result.get(key)
        if isinstance(value, str) and value.strip():
            result[key] = value.strip()
    impact = llm_result.get("impact")
    if impact in {item.value for item in Impact}:
        result["impact"] = impact
        result["impact_label"] = IMPACT_LABELS[Impact(impact)]
    raw_importance = llm_result.get("importance")
    if raw_importance is not None:
        with contextlib.suppress(TypeError, ValueError):
            result["importance"] = max(0, min(100, int(str(raw_importance))))
    for key in ("what_happened", "risks", "opportunities"):
        value = llm_result.get(key)
        if isinstance(value, list) and value:
            result[key] = [str(item) for item in value]
    actions = llm_result.get("actions")
    if isinstance(actions, list) and actions:
        cleaned = []
        for action in actions:
            if isinstance(action, dict) and action.get("title"):
                cleaned.append(
                    {
                        "title": str(action["title"]),
                        "role": str(action.get("role") or "Ответственный"),
                        "deadline": str(action.get("deadline") or "7 дней"),
                        "origin": str(action.get("origin") or "AI"),
                    }
                )
        if cleaned:
            result["actions"] = cleaned
    steps = llm_result.get("agent_steps")
    if isinstance(steps, list) and steps:
        cleaned_steps = []
        for step in steps:
            if isinstance(step, dict) and step.get("text"):
                cleaned_steps.append(
                    {
                        "type": str(step.get("type") or "Шаг"),
                        "text": str(step["text"]),
                    }
                )
        if cleaned_steps:
            result["agent_steps"] = cleaned_steps
    if isinstance(llm_result.get("reporting_used"), bool):
        result["reporting_used"] = llm_result["reporting_used"]
    return result


async def analyze_event(
    profile: BusinessProfile,
    event: NewsEvent,
    business_categories: list[BusinessCategory],
    counterparties: list[Counterparty],
    match_importance: int,
    matched_counterparties: list[str],
    use_llm: bool = True,
) -> dict[str, Any]:
    has_reporting = bool(profile.reporting_summary)
    fallback = fallback_report(
        profile, event, match_importance, matched_counterparties, has_reporting
    )
    if not use_llm:
        return fallback

    context = _profile_context(profile, business_categories, counterparties)
    try:
        llm_result = await get_llm().complete_json(
            system=AGENT_SYSTEM,
            user=agent_prompt(context, _event_context(event)),
            fallback=fallback,
        )
    except Exception:
        logger.exception("Agent LLM failed, using deterministic report")
        return fallback
    return _merge_report(fallback, llm_result)
