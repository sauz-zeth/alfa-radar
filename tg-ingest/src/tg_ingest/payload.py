from datetime import UTC, datetime
from typing import Any


def post_url(chat_id: int, username: str | None, message_id: int) -> str:
    if username:
        return f"https://t.me/{username.lstrip('@')}/{message_id}"
    raw = str(chat_id)
    if raw.startswith("-100"):
        raw = raw[4:]
    return f"https://t.me/c/{raw.lstrip('-')}/{message_id}"


def build_payload(
    *,
    text: str,
    chat_id: int,
    chat_title: str | None,
    username: str | None,
    message_id: int,
    published_at: datetime,
) -> dict[str, Any]:
    handle = f"@{username}" if username else None
    source_name = (chat_title or handle or str(chat_id))[:128]
    return {
        "text": (text or "").strip(),
        "source_name": source_name,
        "channel": handle or source_name,
        "url": post_url(chat_id, username, message_id),
        "published_at": published_at.astimezone(UTC).isoformat(),
        "telegram": {
            "chat_id": chat_id,
            "message_id": message_id,
            "username": username,
        },
    }
