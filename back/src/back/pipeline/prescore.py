from collections.abc import Mapping


def adjusted_probability(probability: float, threshold: float) -> float:
    if threshold >= 1.0 or probability <= threshold:
        return 0.0
    return max(0.0, min(1.0, (probability - threshold) / (1.0 - threshold)))


def category_score(
    category_probabilities: Mapping[str, float],
    category_weights: Mapping[str, float],
    category_thresholds: Mapping[str, float],
) -> float:
    survival = 1.0
    for category, probability in category_probabilities.items():
        weight = category_weights.get(category, 0.0)
        if weight <= 0.0:
            continue
        adjusted = adjusted_probability(probability, category_thresholds.get(category, 0.0))
        survival *= 1.0 - weight * adjusted
    return max(0.0, min(1.0, 1.0 - survival))


def fired_categories(
    category_probabilities: Mapping[str, float],
    category_weights: Mapping[str, float],
    category_thresholds: Mapping[str, float],
) -> list[str]:
    fired: list[str] = []
    for category, probability in category_probabilities.items():
        if category_weights.get(category, 0.0) <= 0.0:
            continue
        if adjusted_probability(probability, category_thresholds.get(category, 0.0)) > 0.0:
            fired.append(category)
    return sorted(fired)
