import math
from collections.abc import Mapping
from dataclasses import dataclass, field

from back.pipeline.prescore import adjusted_probability


@dataclass(slots=True)
class SwipeEffect:
    likes: dict[str, float] = field(default_factory=dict)
    dislikes: dict[str, float] = field(default_factory=dict)


def swipe_effect(
    category_probabilities: Mapping[str, float],
    category_thresholds: Mapping[str, float],
    direction: str,
    reason: str | None = None,
) -> SwipeEffect:
    effect = SwipeEffect()
    if direction == "right":
        factor = 1.0
        target = effect.likes
    elif reason in {"irrelevant", "seen"}:
        return effect
    elif reason == "bad_feed":
        factor = 2.0
        target = effect.dislikes
    elif reason == "not_interesting":
        factor = 1.0
        target = effect.dislikes
    else:
        factor = 0.5
        target = effect.dislikes

    for category, probability in category_probabilities.items():
        adjusted = adjusted_probability(probability, category_thresholds.get(category, 0.0))
        if adjusted > 0.0:
            target[category] = adjusted * factor
    return effect


def category_multiplier(likes: float, dislikes: float) -> float:
    value = math.exp(0.7 * (likes - dislikes) / (likes + dislikes + 5.0))
    return max(0.5, min(1.5, value))


def user_multiplier(
    category_probabilities: Mapping[str, float],
    category_thresholds: Mapping[str, float],
    counters: Mapping[str, tuple[float, float]],
) -> float:
    weighted = 0.0
    total = 0.0
    for category, probability in category_probabilities.items():
        adjusted = adjusted_probability(probability, category_thresholds.get(category, 0.0))
        if adjusted <= 0.0:
            continue
        likes, dislikes = counters.get(category, (0.0, 0.0))
        weighted += adjusted * category_multiplier(likes, dislikes)
        total += adjusted
    if total == 0.0:
        return 1.0
    return weighted / total
