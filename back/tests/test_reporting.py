from back.core.constants import ReportingForm
from back.services.reporting import fallback_extracted


def test_fallback_income_extraction() -> None:
    data = fallback_extracted(
        ReportingForm.INCOME,
        "Отчёт о финансовых результатах 2025\nВыручка 15 200 000 000\nЧистая прибыль 1 400 000 000",
    )
    assert data["period"] == "2025"
    assert data["revenue"] == 15_200_000_000
    assert data["profit"] == 1_400_000_000
