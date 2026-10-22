from datetime import UTC, datetime, timedelta

from back.db.models import BusinessProfile, Company, NewsEvent
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


def test_opportunity_scenarios_are_positive() -> None:
    event = _event(impact="opportunity")
    result = scenarios(event, _profile())
    assert result.scenarios[1].effect > 0


def test_build_insight_contains_mockup_tabs() -> None:
    event = _event()
    profile = _profile()
    insight = build_insight(event, profile, match_event(event, [], []))
    assert insight.theses
    assert insight.comparison.agree
    assert insight.alfa is not None
    assert insight.actions
    assert insight.scenarios.scenarios
    assert insight.agent_log


def test_format_money() -> None:
    assert format_money(-1_390_000_000) == "−1,39 млрд ₽"
    assert format_money(250_000_000) == "+250 млн ₽"
