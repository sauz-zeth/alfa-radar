from collections.abc import Iterable, Sequence

HALF_LIFE_HOURS = {
    "hours": 8.0,
    "days": 24.0,
    "weeks": 72.0,
}

SOURCE_TRUST = {
    1: 0.85,
    2: 0.95,
}


def importance(materiality: int, certainty: int) -> float:
    return 20.0 * materiality * (0.6 + 0.4 * certainty / 5.0)


def source_trust(n_sources: int) -> float:
    if n_sources >= 3:
        return 1.0
    return SOURCE_TRUST.get(max(1, n_sources), 0.85)


def ranking_score(
    event_importance: float,
    age_hours: float,
    horizon: str,
    n_sources: int,
    user_multiplier: float = 1.0,
) -> float:
    half_life = HALF_LIFE_HOURS.get(horizon, HALF_LIFE_HOURS["days"])
    decay = 0.5 ** (max(0.0, age_hours) / half_life)
    return event_importance / 100.0 * decay * source_trust(n_sources) * max(0.0, user_multiplier)


def apply_diversity(
    cards: Sequence[tuple[float, str | None]],
    decay: float = 0.7,
) -> list[float]:
    seen: dict[str, int] = {}
    result: list[float] = []
    for score, category in cards:
        key = category or ""
        count = seen.get(key, 0)
        result.append(score * decay**count)
        seen[key] = count + 1
    return result


def urgent(event_importance: float, seen: bool, limit: int = 2) -> bool:
    return not seen and event_importance >= 85.0 and limit > 0


def pick_top(cards: Iterable[tuple[int, float]], limit: int = 7) -> list[int]:
    ordered = sorted(cards, key=lambda item: item[1], reverse=True)
    return [event_id for event_id, _ in ordered[:limit]]
