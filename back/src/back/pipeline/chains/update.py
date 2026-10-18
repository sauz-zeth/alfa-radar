from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ChainEventSnapshot:
    title: str
    t0: datetime
    what_changed: str | None = None


def build_summary(
    events: Sequence[ChainEventSnapshot],
    limit: int = 3,
) -> str:
    recent = list(events[-limit:])
    lines: list[str] = []
    for event in recent:
        date = event.t0.strftime("%Y-%m-%d")
        line = f"{date}: {event.title}"
        if event.what_changed:
            line = f"{line}. Что изменилось: {event.what_changed}"
        lines.append(line)
    return "\n".join(lines)


def latest_event(events: Sequence[ChainEventSnapshot]) -> ChainEventSnapshot | None:
    if not events:
        return None
    return max(events, key=lambda event: event.t0)
