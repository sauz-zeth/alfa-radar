import asyncio
import contextlib
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
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

BANK_ANALYTICS_DIR = Path(__file__).resolve().parents[3] / "data" / "bank_analytics"

_BANK_STEMS = {
    "пошлин": "пошлин",
    "пошлина": "пошлин",
    "экспорт": "экспорт",
    "экспортн": "экспорт",
    "металлург": "металлург",
    "метал": "металл",
    "сталь": "сталь",
    "прокат": "прокат",
    "ставк": "ставк",
    "инфляц": "инфляц",
    "ключев": "ставк",
}


def _bank_terms(value: str) -> set[str]:
    terms: set[str] = set()
    for token in re.findall(r"[а-яёa-z0-9]+", value.lower()):
        if len(token) < 4:
            continue
        stem = next(
            (stem for prefix, stem in _BANK_STEMS.items() if token.startswith(prefix)),
            token,
        )
        terms.add(stem)
    return terms


def search_bank_analytics(query: str) -> list[dict[str, str]]:
    """Local RAG adapter; Markdown is preferred, PDF remains a fallback."""
    terms = _bank_terms(query)
    if not terms or not BANK_ANALYTICS_DIR.exists():
        return []
    results: list[dict[str, str]] = []
    paths = sorted(BANK_ANALYTICS_DIR.glob("*.md")) + sorted(BANK_ANALYTICS_DIR.glob("*.pdf"))
    for path in paths:
        try:
            if path.suffix.lower() == ".md":
                text = path.read_text(encoding="utf-8", errors="ignore")
            else:
                from pypdf import PdfReader

                text = "\n".join(
                    (page.extract_text() or "") for page in PdfReader(path).pages[:4]
                )
        except Exception:
            continue
        text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
        haystack = f"{path.stem.lower()}\n{text.lower()}"
        score = sum(haystack.count(term) for term in terms)
        if len([term for term in terms if term in haystack]) < min(2, len(terms)):
            continue
        if score:
            excerpt = ""
            for paragraph in (part.strip() for part in re.split(r"\n\s*\n", text)):
                if not paragraph:
                    continue
                if len(excerpt) + len(paragraph) > 1800:
                    break
                excerpt = f"{excerpt}\n\n{paragraph}" if excerpt else paragraph
            results.append(
                {"id": path.name, "title": path.stem, "text": excerpt, "score": str(score)}
            )
    return sorted(results, key=lambda item: int(item["score"]), reverse=True)[:3]


def run_agent_cycle(
    profile: BusinessProfile,
    event: NewsEvent,
    events: list[NewsEvent],
    report: dict[str, Any] | None = None,
    *,
    bank_search: Any = search_bank_analytics,
    max_steps: int = 12,
    on_step: Any = None,
) -> dict[str, Any]:
    """Close report gaps using deterministic tools and retain an auditable journal."""
    state = dict(
        report
        or fallback_report(profile, event, event.importance, [], bool(profile.reporting_summary))
    )
    state.setdefault("what_happened", [])
    state.setdefault("risks", [])
    state.setdefault("opportunities", [])
    state.setdefault("actions", [])
    state.setdefault("alfa", None)
    state.setdefault("field_origins", {})
    for field in ("what_happened", "impact", "risks", "opportunities", "actions", "scenarios"):
        if state.get(field) and field not in state["field_origins"]:
            state["field_origins"][field] = "AI"
    state.setdefault("agent_steps", [])
    state.setdefault("source_ids", [])
    gaps = ["what_happened", "impact", "risks", "opportunities", "scenarios", "actions", "alfa"]
    bank_results: list[dict[str, str]] = []

    def log(tool: str, text: str, **extra: Any) -> None:
        if len(state["agent_steps"]) >= max_steps:
            return
        step = {"type": "Инструмент", "text": text, "tool": tool, **extra}
        state["agent_steps"].append(step)
        if on_step is not None:
            on_step(step)

    def fill(field: str, value: Any, source_ids: list[str]) -> None:
        state[field] = value
        state.setdefault("field_sources", {})[field] = source_ids
        state["field_origins"][field] = "Альфа-Банк" if source_ids and any(
            source_id in state.get("source_ids", []) for source_id in source_ids
        ) else "AI"
        log("fill", f"Заполнено поле «{field}».", field=field, source_ids=source_ids)

    log(
        "get_events",
        f"Загружено событий истории: {len(events)}.",
        source_ids=[str(item.id) for item in events],
    )
    if events:
        source_ids = [str(item.id) for item in events]
        if not state["what_happened"]:
            text = event.summary
            if len(events) > 1:
                previous = sorted(events, key=lambda item: item.published_at)[-2]
                text = (
                    f"{event.summary} Изменение относительно предыдущей новости: "
                    f"{event.title} после «{previous.title}»."
                )
            fill("what_happened", [text], source_ids)
        if len(events) > 1:
            log(
                "diff_events",
                "Сравнены последняя и предыдущая новости истории.",
                source_ids=source_ids[-2:],
            )

    if any(
        field in gaps
        for field in ("impact", "risks", "opportunities", "scenarios", "actions", "alfa")
    ):
        try:
            bank_results = bank_search(f"{event.title} {event.summary}") or []
        except Exception as exc:
            bank_results = []
            state["bank_search_error"] = str(exc)
            state["bank_search_performed"] = False
            log(
                "search_bank_analytics",
                "Поиск аналитики банка завершился ошибкой.",
                error=str(exc),
            )
        else:
            log(
                "search_bank_analytics",
                f"Найдено документов Альфа-Банка: {len(bank_results)}.",
                source_ids=[item["id"] for item in bank_results],
            )
            state["bank_search_performed"] = True
        if bank_results:
            state["source_ids"] = [item["id"] for item in bank_results]
            if "alfa" not in state or not state.get("alfa"):
                fill(
                    "alfa",
                    {"author": "Аналитика Альфа-Банка", "text": bank_results[0]["text"][:500]},
                    [bank_results[0]["id"]],
                )
        elif state.get("bank_search_performed"):
            state["bank_unavailable"] = "У Альфа-Банка нет релевантной аналитики по этой истории."
            state["alfa"] = None
            log("mark_unavailable", state["bank_unavailable"], field="alfa", source_ids=[])
            state["ai_fallback_used"] = True

    if not state.get("risks") and event.impact in {"risk", "mixed"}:
        fill(
            "risks",
            ["Событие может увеличить расходы или снизить выручку компании."],
            [str(event.id)],
        )
        state["field_origins"]["risks"] = "AI"
    if not state.get("opportunities") and event.impact in {"opportunity", "mixed"}:
        fill(
            "opportunities",
            ["Изменение может открыть окно для пересмотра условий или роста выручки."],
            [str(event.id)],
        )
        state["field_origins"]["opportunities"] = "AI"
    if not state.get("risks") and event.impact not in {"risk", "mixed"}:
        state["risks_unavailable"] = (
            "Для нейтрального или позитивного события отдельный риск не выявлен."
        )
        log("mark_unavailable", state["risks_unavailable"], field="risks", source_ids=[])
    if not state.get("opportunities") and event.impact not in {"opportunity", "mixed"}:
        state["opportunities_unavailable"] = (
            "Для нейтрального или негативного события отдельная возможность не выявлена."
        )
        log(
            "mark_unavailable",
            state["opportunities_unavailable"],
            field="opportunities",
            source_ids=[],
        )
    if not state.get("actions"):
        fill("actions", _actions(_role_focus(profile), event.impact), [str(event.id)])
    if not state.get("scenarios"):
        fill(
            "scenarios",
            {"status": "calculated", "horizons": ["3m", "6m", "12m"]},
            [str(event.id)],
        )
        log(
            "calc",
            "Сценарии рассчитаны кодом на горизонтах 3/6/12 месяцев.",
            formula_id="scenario_set",
        )
    unavailable = {
        "alfa" if state.get("bank_unavailable") else "",
        "risks" if state.get("risks_unavailable") else "",
        "opportunities" if state.get("opportunities_unavailable") else "",
    }
    state["agent_gaps"] = [
        field for field in gaps if not state.get(field) and field not in unavailable
    ]
    state["analysis_pending"] = bool(state["agent_gaps"])
    if not state["analysis_pending"]:
        state["analysis_finished_at"] = datetime.now(UTC).strftime("%d.%m %H:%M")
    return state

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
        "impact_metrics": event.impact_metrics,
    }


def chat_context(
    profile: BusinessProfile,
    event: NewsEvent,
    business_categories: list[BusinessCategory],
    counterparties: list[Counterparty],
    report: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "profile": _profile_context(profile, business_categories, counterparties),
        "event": _event_context(event),
        "report": report or {},
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
        "agent_steps": [],
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
                deadline_label = action.get("deadline_label")
                description = action.get("description")
                cleaned.append(
                    {
                        "title": str(action["title"]),
                        "role": str(action.get("role") or "Ответственный"),
                        "description": str(description) if description else None,
                        "deadline": str(action.get("deadline") or "7 дней"),
                        "deadline_label": str(deadline_label) if deadline_label else None,
                        "origin": str(action.get("origin") or "AI"),
                        "is_primary": bool(action.get("is_primary")),
                    }
                )
        if cleaned:
            if not any(item["is_primary"] for item in cleaned):
                cleaned[0]["is_primary"] = True
            primary_seen = False
            for item in cleaned:
                if item["is_primary"]:
                    if primary_seen:
                        item["is_primary"] = False
                    primary_seen = True
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
                        "is_correction": bool(step.get("is_correction")),
                    }
                )
        if cleaned_steps:
            result["agent_steps"] = cleaned_steps

    raw_tiles = llm_result.get("impact_tiles")
    if isinstance(raw_tiles, list) and raw_tiles:
        tiles = []
        for tile in raw_tiles:
            if not isinstance(tile, dict):
                continue
            tile_type = str(tile.get("type") or "")
            label = str(tile.get("label") or "").strip()
            if tile_type not in {"metric", "statement", "accent"} or not label:
                continue
            value = tile.get("value")
            note = tile.get("note")
            span = str(tile.get("span") or "half")
            tiles.append(
                {
                    "type": tile_type,
                    "value": str(value) if value is not None else None,
                    "label": label,
                    "note": str(note) if note is not None else None,
                    "span": span if span in {"half", "full"} else "half",
                }
            )
        if tiles:
            result["impact_tiles"] = tiles[:8]

    raw_questions = llm_result.get("open_questions")
    if isinstance(raw_questions, list) and raw_questions:
        questions = []
        for question in raw_questions:
            if not isinstance(question, dict):
                continue
            text = str(question.get("text") or "").strip()
            if not text:
                continue
            questions.append(
                {
                    "text": text,
                    "source": str(question["source"]) if question.get("source") else None,
                }
            )
        if questions:
            result["open_questions"] = questions[:5]

    raw_checklist = llm_result.get("checklist")
    if isinstance(raw_checklist, list) and raw_checklist:
        checklist = [str(item).strip() for item in raw_checklist if str(item).strip()]
        if checklist:
            result["checklist"] = checklist[:6]

    alfa = llm_result.get("alfa")
    if isinstance(alfa, dict):
        text = str(alfa.get("text") or "").strip()
        if text:
            author = str(alfa.get("author") or "").strip()
            result["alfa"] = {"author": author or "Аналитика Альфа-Банка", "text": text}

    if isinstance(llm_result.get("reporting_used"), bool):
        result["reporting_used"] = llm_result["reporting_used"]
    return result


def pending_report(fallback: dict[str, Any]) -> dict[str, Any]:
    report = dict(fallback)
    report.pop("analysis_finished_at", None)
    report["analysis_pending"] = True
    report["agent_steps"] = []
    return report


async def analyze_event(
    profile: BusinessProfile,
    event: NewsEvent,
    business_categories: list[BusinessCategory],
    counterparties: list[Counterparty],
    match_importance: int,
    matched_counterparties: list[str],
    use_llm: bool = True,
    events: list[NewsEvent] | None = None,
    on_step: Any = None,
) -> dict[str, Any]:
    has_reporting = bool(profile.reporting_summary)
    fallback = fallback_report(
        profile, event, match_importance, matched_counterparties, has_reporting
    )
    report = dict(fallback)
    report["agent_steps"] = []
    emitted_steps: list[dict[str, Any]] = []

    async def emit(step: dict[str, Any]) -> None:
        emitted_steps.append(step)
        if on_step is not None:
            await on_step(step)

    if on_step is not None:
        await emit(
            {"type": "Анализ", "text": "Агент начал анализ новости.", "tool": "llm_analysis"}
        )
    if use_llm:
        context = _profile_context(profile, business_categories, counterparties)
        try:
            llm_result = await get_llm().complete_json(
                system=AGENT_SYSTEM,
                user=agent_prompt(context, _event_context(event)),
                fallback=fallback,
            )
        except Exception:
            logger.exception("Agent LLM failed, using deterministic report")
        else:
            report = _merge_report(fallback, llm_result)
    if on_step is None:
        report = run_agent_cycle(profile, event, events or [event], report)
    else:
        loop = asyncio.get_running_loop()
        report = await asyncio.to_thread(
            run_agent_cycle, profile, event, events or [event], report,
            on_step=lambda step: asyncio.run_coroutine_threadsafe(
                emit(step), loop
            ).result(),
        )
        report["agent_steps"] = emitted_steps
    report["analysis_finished_at"] = datetime.now(UTC).strftime("%d.%m %H:%M")
    return report
