import pytest

from back.pipeline.prescore import adjusted_probability, category_score, fired_categories


def test_probability_below_threshold_is_zero() -> None:
    assert adjusted_probability(0.15, 0.3) == 0.0


def test_probability_is_rescaled_above_threshold() -> None:
    assert adjusted_probability(0.65, 0.3) == pytest.approx(0.5)


def test_noisy_or_stays_below_one() -> None:
    score = category_score(
        {"ставка": 1.0, "курс": 1.0, "спрос": 1.0},
        {"ставка": 0.6, "курс": 0.6, "спрос": 0.6},
        {},
    )
    assert 0.9 < score < 1.0


def test_weak_noise_across_many_categories_is_filtered() -> None:
    probabilities = {f"category_{index}": 0.15 for index in range(10)}
    weights = {f"category_{index}": 0.6 for index in range(10)}
    thresholds = {f"category_{index}": 0.3 for index in range(10)}
    assert category_score(probabilities, weights, thresholds) == 0.0


def test_single_category_matches_weighted_probability() -> None:
    score = category_score({"ставка": 1.0}, {"ставка": 0.6}, {"ставка": 0.0})
    assert score == pytest.approx(0.6)


def test_fired_categories_ignore_zero_weight() -> None:
    fired = fired_categories(
        {"ставка": 0.9, "курс": 0.9},
        {"ставка": 0.6},
        {"ставка": 0.3},
    )
    assert fired == ["ставка"]
