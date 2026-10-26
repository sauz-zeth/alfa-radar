from datetime import UTC, datetime
from uuid import uuid4

from back.db.models import (
    BusinessCategory,
    BusinessProfile,
    Counterparty,
    EventAnalysis,
    NewsEvent,
    ProfileEventScore,
)
from back.services.feed import event_to_feed_item, match_event


def _event() -> NewsEvent:
    return NewsEvent(
        title="ЦБ сохранил ставку",
        summary="...",
        what_it_means="...",
        source_name="ЦБ",
        published_at=datetime.now(UTC),
        importance=80,
        impact="mixed",
        category_ids=[1, 2],
        mentioned_company_uids=["U_SUPPLIER"],
        facts=[],
    )


def test_match_event_categories_and_counterparty() -> None:
    categories = [BusinessCategory(category_id=1, weight=1.0)]
    counterparties = [
        Counterparty(
            company_uid="U_SUPPLIER",
            default_name="Поставщик 1",
            direction="supplier",
            importance=90,
        )
    ]
    result = match_event(_event(), categories, counterparties)
    assert result.importance == 95
    assert result.matched_categories[0].id == 1
    assert result.matched_counterparties == ["Поставщик 1"]


def test_what_it_means_uses_profile_theses_from_kimi() -> None:
    event = NewsEvent(
        id=uuid4(),
        title="ЦБ сохранил ставку",
        summary="...",
        what_it_means="...",
        source_name="ЦБ",
        published_at=datetime.now(UTC),
        importance=80,
        impact="mixed",
        category_ids=[1, 2],
        mentioned_company_uids=[],
        facts=[],
    )
    profile = BusinessProfile(
        entrepreneur_name="Тест", business_name="Бизнес", role="cfo", sources={},
        reporting_summary={},
    )
    analysis = EventAnalysis(
        related=True, direct=True, fact=True, within_month=False, independent_source_count=1,
        why=[{"highlight": "Маржа", "text": "может снизиться"}],
    )
    item = event_to_feed_item(
        event, match_event(event, [], [], profile_importance=85), profile=profile, analysis=analysis
    )
    assert item.what_it_means == "Маржа может снизиться"


def test_feed_item_uses_profile_score_theses_and_lists_sources() -> None:
    event = _event()
    event.id = uuid4()
    event.source_posts = [{"name": "Минфин", "text": "Ставка сохранена", "url": "https://example.com"}]
    score = ProfileEventScore(
        importance=85,
        related=True,
        direct=True,
        fact=True,
        within_month=False,
        why=[{"highlight": "Маржа", "text": "может снизиться"}],
        independent_source_count=1,
    )
    item = event_to_feed_item(
        event, match_event(event, [], [], profile_importance=score.importance),
        profile=BusinessProfile(
            entrepreneur_name="Тест", business_name="Бизнес", role="cfo", sources={},
            reporting_summary={},
        ),
        analysis=score,
    )

    assert item.importance == 85
    assert item.what_it_means == "Маржа может снизиться"
    assert item.source_count == 1
    assert item.sources[0].name == "Минфин"


def test_feed_item_fallback_is_short_and_does_not_repeat_news() -> None:
    event = _event()
    event.id = uuid4()
    event.summary = "Длинная новость, которая не должна повторяться в объяснении."
    score = ProfileEventScore(
        importance=55,
        related=True,
        direct=False,
        fact=True,
        within_month=True,
        why=[],
        independent_source_count=1,
    )
    item = event_to_feed_item(
        event,
        match_event(event, [], [], profile_importance=score.importance),
        profile=BusinessProfile(
            entrepreneur_name="Тест", business_name="Бизнес", role="cfo", sources={},
            reporting_summary={},
        ),
        analysis=score,
    )

    assert item.what_it_means == "Событие связано с профилем вашего бизнеса."
