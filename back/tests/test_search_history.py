from back.db.models import BusinessProfile
from back.services.search import (
    _rank_events_by_embedding,
    clear_history,
    remember_query,
    remove_history,
    search_history,
)


def _profile() -> BusinessProfile:
    return BusinessProfile(
        entrepreneur_name="Иван",
        business_name="Тест",
        search_history=[],
        sources={},
        notifications={},
    )


def test_history_deduplicates_and_limits() -> None:
    profile = _profile()
    for index in range(12):
        remember_query(profile, f"запрос {index}")
    remember_query(profile, "запрос 5")
    items = search_history(profile).items
    assert len(items) == 10
    assert items[0].query == "запрос 5"
    assert sum(item.query == "запрос 5" for item in items) == 1


def test_history_remove_and_clear() -> None:
    profile = _profile()
    remember_query(profile, "ставка")
    remember_query(profile, "пошлины")
    target = search_history(profile).items[1]
    assert remove_history(profile, target.id)
    assert all(item.id != target.id for item in search_history(profile).items)
    clear_history(profile)
    assert search_history(profile).items == []


def test_short_query_not_remembered() -> None:
    profile = _profile()
    remember_query(profile, "a")
    assert search_history(profile).items == []


def test_embedding_search_ranks_events_and_keeps_best_post_score() -> None:
    from uuid import uuid4

    first, second = uuid4(), uuid4()
    ranked = _rank_events_by_embedding(
        [
            (first, [1.0, 0.0]),
            (first, [0.8, 0.6]),
            (second, [0.0, 1.0]),
        ],
        [1.0, 0.0],
    )
    assert ranked == [(first, 1.0), (second, 0.0)]
