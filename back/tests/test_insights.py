from datetime import UTC, datetime, timedelta

from back.db.models import BusinessProfile, Company, NewsEvent
from back.services.agent import _merge_report
from back.services.feed import match_event
from back.services.insights import (
    build_insight,
    format_money,
    scenarios,
    score_breakdown,
    source_posts,
)


def _event(**overrides) -> NewsEvent:
    values = {
        "title": "Повышены экспортные пошлины на металлопрокат",
        "summary": "Правительство повысило пошлины.",
        "what_it_means": "Снижается маржа экспортёров.",
        "source_name": "Правительство РФ",
        "published_at": datetime.now(UTC) - timedelta(hours=2),
        "importance": 80,
        "impact": "risk",
        "category_ids": [4, 15],
        "mentioned_company_uids": [],
        "facts": [{"text": "Пошлина вступает с 1 ноября", "status": "Официально"}],
        "source_posts": [
            {
                "name": "Правительство РФ",
                "time": datetime.now(UTC).isoformat(),
                "tone": "official",
                "text": "Постановление опубликовано.",
                "is_primary": True,
            },
            {
                "name": "Деловой вестник",
                "time": datetime.now(UTC).isoformat(),
                "tone": "neutral",
                "text": "Ставка составит 7%.",
            },
        ],
    }
    values.update(overrides)
    return NewsEvent(**values)


def _profile() -> BusinessProfile:
    company = Company(
        uid="U_TEST",
        main_okved_name="Металлургия",
        revenue=52_000_000_000,
        revenue_segment="крупнейший",
        tags=[],
    )
    return BusinessProfile(
        entrepreneur_name="Андрей Волков",
        business_name="ТрансМеталл",
        role="cfo",
        company=company,
        sources={},
        reporting_summary={},
    )


def test_source_posts_uses_stored_sources() -> None:
    posts = source_posts(_event())
    assert len(posts) == 2
    assert posts[0].is_primary
    assert posts[1].name == "Деловой вестник"


def test_score_breakdown_has_four_components() -> None:
    event = _event()
    profile = _profile()
    match = match_event(event, [], [])
    components, why, share = score_breakdown(event, match, profile)
    assert [item.key for item in components] == ["scale", "directness", "urgency", "novelty"]
    assert why
    assert share
    assert all(1 <= item.value <= 5 for item in components)


def test_scenarios_are_signed_and_scale_with_horizon() -> None:
    event = _event()
    profile = _profile()
    short = scenarios(event, profile, "3m")
    full = scenarios(event, profile, "12m")
    assert short.scenarios[1].effect < 0
    assert abs(full.scenarios[1].effect) > abs(short.scenarios[1].effect)
    assert full.scenarios[0].effect < full.scenarios[1].effect < full.scenarios[2].effect


def test_opportunity_scenarios_are_positive_and_ordered() -> None:
    event = _event(impact="opportunity")
    result = scenarios(event, _profile())
    assert result.scenarios[1].effect > 0
    assert result.scenarios[0].effect < result.scenarios[1].effect < result.scenarios[2].effect


def test_build_insight_without_report_has_no_canned_content() -> None:
    event = _event()
    profile = _profile()
    insight = build_insight(event, profile, match_event(event, [], []))
    assert insight.theses
    assert insight.comparison.agree
    assert insight.alfa is None
    assert insight.actions == []
    assert insight.agent_log == []
    assert insight.checklist == []
    assert insight.chat == []
    assert insight.impact_tiles == []
    assert insight.open_questions == []
    assert insight.scenarios.scenarios


def test_build_insight_uses_stored_report() -> None:
    event = _event()
    profile = _profile()
    report = {
        "alfa": {"author": "Аналитики банка", "text": "Текст аналитики."},
        "impact_tiles": [
            {
                "type": "statement",
                "value": "Главный вывод",
                "label": "Вывод",
                "note": "Пояснение",
                "span": "full",
            }
        ],
        "checklist": ["Проверить договор"],
        "actions": [
            {
                "id": "a1",
                "title": "Сделать расчёт",
                "role": "CFO",
                "description": "Описание действия",
                "deadline_label": "2 дня",
                "is_primary": True,
                "origin": "Банк",
            }
        ],
        "agent_steps": [
            {
                "type": "Исправление",
                "text": "Уточнили вывод",
                "is_correction": True,
                "at": "10:00",
            }
        ],
        "chat": [{"question": "Вопрос", "answer": "Ответ", "origin": "AI"}],
        "open_questions": [
            {"id": "q1", "text": "Что дальше?", "status": "Ждём", "status_code": "waiting"}
        ],
        "scenario_origins": ["Банк", "Банк", "Модель"],
        "forecast_note": "Прогноз обновлён.",
        "analysis_finished_at": "24.10 12:00",
    }

    insight = build_insight(event, profile, match_event(event, [], []), report)

    assert insight.alfa is not None
    assert insight.alfa.text == "Текст аналитики."
    assert insight.impact_tiles[0].type == "statement"
    assert insight.impact_tiles[0].span == "full"
    assert insight.checklist == ["Проверить договор"]
    assert insight.actions[0].id == "a1"
    assert insight.actions[0].description == "Описание действия"
    assert insight.actions[0].deadline_label == "2 дня"
    assert insight.actions[0].is_primary
    assert insight.agent_log[0].is_correction
    assert insight.agent_log[0].at == "10:00"
    assert insight.chat[0].answer == "Ответ"
    assert insight.open_questions[0].text == "Что дальше?"
    assert insight.scenarios.forecast_note == "Прогноз обновлён."
    assert [scenario.origin for scenario in insight.scenarios.scenarios] == [
        "Банк",
        "Банк",
        "Модель",
    ]
    assert [scenario.share for scenario in insight.scenarios.scenarios] == ["0%", "15%", "50%"]
    assert [scenario.is_base for scenario in insight.scenarios.scenarios] == [
        False,
        True,
        False,
    ]
    assert insight.analysis_finished_at == "24.10 12:00"


def test_impact_tiles_derive_from_event_metrics() -> None:
    event = _event(
        impact_metrics=[
            {"label": "Метрика 1", "value": "10%"},
            {"label": "Метрика 2", "value": "20%"},
            {"label": "Метрика 3", "value": "30%", "note": "Первая строка\nВторая строка"},
        ]
    )
    insight = build_insight(event, _profile(), match_event(event, [], []))
    assert [tile.value for tile in insight.impact_tiles] == ["30%"]
    assert all(tile.type == "metric" and tile.span == "half" for tile in insight.impact_tiles)
    assert insight.impact_tiles[0].note == "Первая строка Вторая строка"


def test_format_money() -> None:
    assert format_money(-1_390_000_000) == "−1,39 млрд ₽"
    assert format_money(250_000_000) == "+250 млн ₽"


def test_merge_report_passes_agent_ui_fields() -> None:
    merged = _merge_report(
        {},
        {
            "impact_tiles": [
                {
                    "type": "accent",
                    "value": "92 / 100",
                    "label": "Важность",
                    "note": "риск",
                    "span": "half",
                },
                {"type": "unknown", "label": "bad"},
            ],
            "open_questions": [{"text": "Кто платит пошлину?", "source": "Минфин"}],
            "checklist": ["Проверить контракты", ""],
            "alfa": {"author": "Отдел анализа", "text": "Комментарий банка."},
            "actions": [
                {
                    "title": "Проверить контракты",
                    "role": "CFO",
                    "description": "Сверить условия.",
                    "deadline": "3 дня",
                    "deadline_label": "до 31 октября",
                    "is_primary": True,
                },
                {"title": "Проверить бюджет", "is_primary": True},
            ],
            "agent_steps": [{"type": "Проверка", "text": "Исправил базу.", "is_correction": True}],
        },
    )
    assert merged["impact_tiles"] == [
        {
            "type": "accent",
            "value": "92 / 100",
            "label": "Важность",
            "note": "риск",
            "span": "half",
        }
    ]
    assert merged["open_questions"] == [{"text": "Кто платит пошлину?", "source": "Минфин"}]
    assert merged["checklist"] == ["Проверить контракты"]
    assert merged["alfa"] == {"author": "Отдел анализа", "text": "Комментарий банка."}
    assert merged["actions"][0]["deadline_label"] == "до 31 октября"
    assert [item["is_primary"] for item in merged["actions"]] == [True, False]
    assert merged["agent_steps"][0]["is_correction"] is True
