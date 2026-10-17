def should_push(
    conclusions_changed: bool,
    event_importance: float,
    pushes_today: int,
    daily_limit: int = 3,
) -> bool:
    if pushes_today >= daily_limit:
        return False
    return conclusions_changed or event_importance >= 50.0


def push_text(chain_title: str, what_changed: str) -> str:
    return f"Обновление: {chain_title}. {what_changed}".strip()
