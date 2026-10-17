from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Candidate:
    event_id: int
    prescore: float
    has_mention: bool


def select_for_llm(
    candidates: Sequence[Candidate],
    tau: float,
    limit: int,
) -> list[Candidate]:
    eligible = [
        candidate for candidate in candidates if candidate.prescore >= tau or candidate.has_mention
    ]
    eligible.sort(key=lambda item: (item.has_mention, item.prescore), reverse=True)
    return eligible[: max(0, limit)]
