from back.core.recommendations import (
    BROAD_GENERAL_TOPICS,
    GENERAL_CATEGORY_IDS,
    candidates,
    recommend_ids,
    source_category_ids,
)
from back.core.sources import CHANNELS

DEMO_CATEGORIES = {1, 2, 3, 4, 5, 6, 12, 15, 23}


def test_every_catalog_source_has_categories() -> None:
    assert all(candidate.category_ids for candidate in candidates())
    assert len(candidates()) == len(CHANNELS)


def test_demo_profile_recommendations_are_balanced() -> None:
    ids = recommend_ids(DEMO_CATEGORIES)
    chosen = [item for item in candidates() if item.id in ids]
    broad = [item for item in chosen if item.is_general]

    assert len(ids) == 50
    assert len(set(ids)) == 50
    assert len(chosen) == 50
    assert len([item for item in chosen if item.source_type == "telegram"]) == 25
    assert len([item for item in chosen if item.source_type == "rss"]) == 25
    assert 10 <= len(broad) <= 20


def test_general_sources_are_always_present_for_narrow_profile() -> None:
    chosen = [item for item in candidates() if item.id in recommend_ids({15})]
    broad = [item for item in chosen if item.is_general]
    assert broad
    assert chosen


def test_rss_sources_rank_by_importance() -> None:
    popularity = {item.name: item.popularity for item in candidates()}
    regional = popularity["63.ру (Самара)"]
    assert popularity["Банк России — события"] > popularity["Комсомольская правда"]
    assert popularity["The New York Times — Business"] > regional
    assert popularity["Financial Times"] > regional
    assert popularity["Al Jazeera"] > regional


def test_rss_section_overrides_do_not_mix_unrelated_industries() -> None:
    by_name = {item.name: item for item in CHANNELS}
    assert source_category_ids(by_name["Учительская газета"]) == {26}
    assert source_category_ids(by_name["New Retail"]) == {22}
    assert source_category_ids(by_name["Drom.ru — новости"]) == {21}
    assert 16 not in source_category_ids(by_name["Газета.Ru"])


def test_industry_source_categories() -> None:
    metals = next(item for item in CHANNELS if item.id == "nerzhavey")
    assert 15 in source_category_ids(metals)
    interfax = next(
        item for item in CHANNELS if item.id.startswith("rss_") and "Интерфакс" in item.name
    )
    assert interfax.topics in BROAD_GENERAL_TOPICS
    assert source_category_ids(interfax) & GENERAL_CATEGORY_IDS
