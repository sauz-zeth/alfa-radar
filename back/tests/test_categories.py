from back.db.models import Company
from back.services.categories import heuristic_category_weights


def test_heuristic_categories_for_metals() -> None:
    company = Company(
        uid="U_TEST",
        main_okved_code="24.10",
        main_okved_name="Производство чугуна, стали и ферросплавов",
        revenue=20_000_000_000,
        revenue_segment="крупнейший",
        cl_product_loa_mark=True,
        cl_product_lea_mark=False,
        cl_product_rko_mark=True,
        cl_product_zpp_mark=True,
        cl_product_dep_mark=False,
        cl_product_gar_mark=False,
        fts_flag=True,
        fts_country_name="Турция",
        city="г. Москва",
        region="Москва",
        amount_workers_fns_gradation="500+",
        company_age_years_gradation="10+",
        eco_mark_label="Зрелость",
        org_type="КОММ_ОРГ",
    )
    items = heuristic_category_weights(company)
    weights = {item["category_id"]: item["weight"] for item in items}
    assert weights[15] == 1.0
    assert weights[1] >= 0.6
    assert 2 in weights and 3 in weights and 4 in weights
