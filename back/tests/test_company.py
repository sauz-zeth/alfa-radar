from back.core.company import company_tags, revenue_segment


def test_revenue_segment_thresholds() -> None:
    assert revenue_segment(None) == "неизвестен"
    assert revenue_segment(50_000_000) == "микро"
    assert revenue_segment(500_000_000) == "малый"
    assert revenue_segment(1_500_000_000) == "средний"
    assert revenue_segment(10_000_000_000) == "крупный"
    assert revenue_segment(20_000_000_000) == "крупнейший"


def test_company_tags() -> None:
    tags = company_tags(
        {
            "main_okved_name": "Торговля оптовая нефтью и газом",
            "city": "г. Москва",
            "region": "Москва",
            "fts_flag": True,
            "fts_country_name": "Казахстан",
            "cl_product_loa_mark": True,
        }
    )
    assert "нефтегаз" in tags
    assert "ВЭД" in tags
    assert "кредитная нагрузка" in tags
