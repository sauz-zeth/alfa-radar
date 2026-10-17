import pytest

from back.services.feedback import (
    category_multiplier,
    swipe_effect,
    user_multiplier,
)


def test_right_swipe_adds_like_signal() -> None:
    effect = swipe_effect({"ставка": 0.65}, {"ставка": 0.3}, "right")
    assert effect.likes["ставка"] == pytest.approx(0.5)
    assert effect.dislikes == {}


def test_bad_feed_doubles_dislike() -> None:
    effect = swipe_effect({"ставка": 0.65}, {"ставка": 0.3}, "left", "bad_feed")
    assert effect.dislikes["ставка"] == pytest.approx(1.0)


def test_left_without_reason_uses_half_signal() -> None:
    effect = swipe_effect({"ставка": 0.65}, {"ставка": 0.3}, "left", None)
    assert effect.dislikes["ставка"] == pytest.approx(0.25)


def test_irrelevant_swipe_does_not_change_counters() -> None:
    effect = swipe_effect({"ставка": 0.65}, {"ставка": 0.3}, "left", "irrelevant")
    assert effect.likes == {}
    assert effect.dislikes == {}


def test_category_multiplier_is_clipped() -> None:
    assert category_multiplier(1000.0, 0.0) == 1.5
    assert category_multiplier(0.0, 1000.0) == 0.5
    assert category_multiplier(0.0, 0.0) == pytest.approx(1.0)


def test_user_multiplier_without_categories_is_neutral() -> None:
    assert user_multiplier({}, {}, {}) == 1.0
