from datetime import UTC, datetime

from tg_ingest.payload import build_payload, post_url


def test_public_channel_url() -> None:
    assert post_url(-1001234567890, "metall_inside", 42) == "https://t.me/metall_inside/42"
    assert post_url(1234567890, "@metall_inside", 42) == "https://t.me/metall_inside/42"


def test_private_channel_url() -> None:
    assert post_url(1234567890, None, 42) == "https://t.me/c/1234567890/42"
    assert post_url(-1001234567890, None, 42) == "https://t.me/c/1234567890/42"


def test_payload() -> None:
    payload = build_payload(
        text="  Цена стали выросла\nПодробнее внутри  ",
        chat_id=1234567890,
        chat_title="Металл-Инсайд",
        username="metall_inside",
        message_id=42,
        published_at=datetime(2026, 10, 25, 12, 0, tzinfo=UTC),
    )
    assert payload["text"] == "Цена стали выросла\nПодробнее внутри"
    assert payload["source_name"] == "Металл-Инсайд"
    assert payload["channel"] == "@metall_inside"
    assert payload["url"] == "https://t.me/metall_inside/42"
    assert payload["published_at"] == "2026-10-25T12:00:00+00:00"
    assert payload["telegram"]["message_id"] == 42


def test_payload_without_username() -> None:
    payload = build_payload(
        text="Пост",
        chat_id=1234567890,
        chat_title=None,
        username=None,
        message_id=7,
        published_at=datetime(2026, 10, 25, 12, 0, tzinfo=UTC),
    )
    assert payload["source_name"] == "1234567890"
    assert payload["channel"] == "1234567890"
    assert payload["url"] == "https://t.me/c/1234567890/7"
