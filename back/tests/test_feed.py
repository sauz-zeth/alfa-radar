from datetime import UTC, datetime

from back.db.models import BusinessCategory, Counterparty, NewsEvent
from back.services.feed import match_event


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
