import pytest

from back.pipeline.rank import (
    apply_diversity,
    importance,
    pick_top,
    ranking_score,
    source_trust,
    urgent,
)


def test_importance_range() -> None:
    assert importance(5, 5) == 100.0
    assert importance(1, 1) == pytest.approx(13.6)


def test_source_trust() -> None:
    assert source_trust(1) == 0.85
    assert source_trust(2) == 0.95
    assert source_trust(5) == 1.0


def test_ranking_without_age_decay() -> None:
    score = ranking_score(100.0, 0.0, "days", 3)
    assert score == pytest.approx(1.0)


def test_half_life_depends_on_horizon() -> None:
    hours = ranking_score(100.0, 8.0, "hours", 3)
    days = ranking_score(100.0, 8.0, "days", 3)
    weeks = ranking_score(100.0, 8.0, "weeks", 3)
    assert hours == pytest.approx(0.5)
    assert weeks > days > hours


def test_diversity_penalizes_repeated_category() -> None:
    scores = apply_diversity([(1.0, "ставка"), (1.0, "ставка"), (1.0, "курс")])
    assert scores[1] == pytest.approx(0.7)
    assert scores[2] == pytest.approx(1.0)


def test_urgent_requires_unseen_high_importance() -> None:
    assert urgent(90.0, seen=False)
    assert not urgent(90.0, seen=True)
    assert not urgent(50.0, seen=False)


def test_pick_top_orders_by_score() -> None:
    assert pick_top([(1, 0.2), (2, 0.9), (3, 0.5)], limit=2) == [2, 3]
