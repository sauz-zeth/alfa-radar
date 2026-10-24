from back.core.constants import ReportingForm
from back.services.reporting import fallback_extracted, form_markdown


def test_fallback_income_extraction() -> None:
    data = fallback_extracted(
        ReportingForm.INCOME,
        "Отчёт о финансовых результатах 2025\nВыручка 15 200 000 000\nЧистая прибыль 1 400 000 000",
    )
    assert data["period"] == "2025"
    assert data["revenue"] == 15_200_000_000
    assert data["profit"] == 1_400_000_000


def test_form_markdown_has_headings_tables_and_lists() -> None:
    markdown = form_markdown(
        ReportingForm.INCOME,
        "income.xlsx",
        {
            "period": "2025",
            "revenue": 1_000_000_000,
            "profit": 120_000_000,
            "cash_flows": {"operating": 300_000_000},
            "key_points": ["Выручка выросла на 12%"],
        },
    )
    assert "## Отчёт о финансовых результатах" in markdown
    assert "**Период:** 2025" in markdown
    assert "| Показатель | Значение |" in markdown
    assert "| Выручка | 1 млрд ₽ |" in markdown
    assert "- Выручка выросла на 12%" in markdown
