"""Simulated Outlook integration.

The hackathon environment has no Microsoft tenant, so the provider is modelled:
the UI and API follow the real flow (connect, compose, draft, send, statuses,
reminders, replies), while the state is persisted in ``BusinessProfile.outlook_state``.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any, cast

from back.db.models import BusinessProfile, Counterparty
from back.schemas.outlook import (
    OutlookConnectRequest,
    OutlookContact,
    OutlookMessageCreate,
    OutlookMessageOut,
    OutlookMessagePatch,
    OutlookRecipient,
    OutlookStateOut,
    OutlookStatus,
)

OUTLOOK_SCOPES = [
    "Mail.Send",
    "Mail.ReadWrite",
    "Mail.ReadBasic",
]

STATUS_FLOW: tuple[str, ...] = ("draft", "sent", "delivered", "read", "replied")
STATUS_LABELS: dict[str, str] = {
    "draft": "Черновик",
    "sent": "Отправлено",
    "delivered": "Доставлено",
    "read": "Прочитано",
    "replied": "Ответ получен",
}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class OutlookError(ValueError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime | None = None) -> str:
    return (value or _now()).isoformat()


def _state(profile: BusinessProfile) -> dict[str, Any]:
    return dict(profile.outlook_state or {})


def _save(profile: BusinessProfile, state: dict[str, Any]) -> None:
    state["updated_at"] = _iso()
    profile.outlook_state = state


def _account(state: dict[str, Any]) -> dict[str, Any]:
    account = state.get("account")
    return dict(account) if isinstance(account, dict) else {}


def _messages(state: dict[str, Any]) -> list[dict[str, Any]]:
    messages = state.get("messages")
    if not isinstance(messages, list):
        return []
    return [dict(item) for item in messages if isinstance(item, dict)]


def _require_connected(profile: BusinessProfile) -> dict[str, Any]:
    account = _account(_state(profile))
    if not account.get("connected") or not account.get("email"):
        raise OutlookError("Сначала подключите Outlook", status_code=409)
    return account


def _recipient_payload(items: list[OutlookRecipient]) -> list[dict[str, str]]:
    if not items:
        raise OutlookError("Укажите хотя бы одного получателя")
    result: list[dict[str, str]] = []
    for item in items:
        email = item.email.strip()
        if not EMAIL_RE.match(email):
            raise OutlookError(f"Неверный адрес: {item.email}")
        result.append({"name": item.name.strip(), "email": email})
    return result


def _public(message: dict[str, Any]) -> OutlookMessageOut:
    status = cast(OutlookStatus, str(message.get("status") or "draft"))
    return OutlookMessageOut(
        id=str(message["id"]),
        event_id=str(message["event_id"]),
        action_id=message.get("action_id"),
        subject=str(message.get("subject") or ""),
        body=str(message.get("body") or ""),
        to=[OutlookRecipient(**item) for item in message.get("to") or []],
        cc=[OutlookRecipient(**item) for item in message.get("cc") or []],
        importance=message.get("importance") or "normal",
        due_at=message.get("due_at"),
        status=status,
        status_label=STATUS_LABELS.get(status, status),
        thread_id=str(message.get("thread_id") or message["id"]),
        attachment_name=message.get("attachment_name"),
        reminder_count=int(message.get("reminder_count") or 0),
        created_at=str(message.get("created_at") or _iso()),
        updated_at=str(message.get("updated_at") or _iso()),
        sent_at=message.get("sent_at"),
        read_at=message.get("read_at"),
        replied_at=message.get("replied_at"),
        last_reminder_at=message.get("last_reminder_at"),
    )


def get_state(profile: BusinessProfile, event_id: str | None = None) -> OutlookStateOut:
    state = _state(profile)
    account = _account(state)
    messages = _messages(state)
    if event_id:
        messages = [item for item in messages if str(item.get("event_id")) == event_id]
    messages.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
    connected = bool(account.get("connected") and account.get("email"))
    return OutlookStateOut(
        connected=connected,
        email=account.get("email"),
        scopes=list(account.get("scopes") or []),
        messages=[_public(item) for item in messages],
    )


def connect(profile: BusinessProfile, payload: OutlookConnectRequest) -> OutlookStateOut:
    email = payload.email.strip()
    if not EMAIL_RE.match(email):
        raise OutlookError("Введите корректный адрес электронной почты")
    state = _state(profile)
    state["account"] = {
        "email": email,
        "connected": True,
        "connected_at": _iso(),
        "scopes": list(OUTLOOK_SCOPES),
        "provider": "mock",
    }
    _save(profile, state)
    return get_state(profile)


def disconnect(profile: BusinessProfile) -> OutlookStateOut:
    state = _state(profile)
    account = _account(state)
    if account:
        account["connected"] = False
        account["disconnected_at"] = _iso()
        state["account"] = account
        _save(profile, state)
    return get_state(profile)


def contacts(
    profile: BusinessProfile,
    counterparties: Iterable[Counterparty],
    query: str = "",
) -> list[OutlookContact]:
    state = _state(profile)
    account = _account(state)
    items: list[OutlookContact] = []

    if account.get("email"):
        items.append(
            OutlookContact(
                name=profile.entrepreneur_name or "Вы",
                email=str(account["email"]),
                role=profile.role_label or "Пользователь",
                source="account",
            )
        )

    items.extend(
        [
            OutlookContact(
                name="Финансовый директор",
                email="cfo@company.example",
                role="Финансы",
                source="team",
            ),
            OutlookContact(
                name="Главный бухгалтер",
                email="accountant@company.example",
                role="Бухгалтерия",
                source="team",
            ),
            OutlookContact(
                name="Юрист",
                email="lawyer@company.example",
                role="Право",
                source="team",
            ),
            OutlookContact(
                name="Менеджер по закупкам",
                email="procurement@company.example",
                role="Закупки",
                source="team",
            ),
        ]
    )

    for index, item in enumerate(counterparties, start=1):
        direction = "Поставщик" if item.direction == "supplier" else "Покупатель"
        items.append(
            OutlookContact(
                name=item.display_name,
                email=f"partner{index}@example.ru",
                role=direction,
                source="counterparty",
            )
        )

    term = query.strip().lower()
    if term:
        items = [
            item
            for item in items
            if term in item.name.lower()
            or term in item.email.lower()
            or term in item.role.lower()
        ]
    return items


def create_message(
    profile: BusinessProfile,
    payload: OutlookMessageCreate,
) -> OutlookMessageOut:
    _require_connected(profile)
    subject = payload.subject.strip()
    body = payload.body.strip()
    if not subject or not body:
        raise OutlookError("Заполните тему и текст письма")
    state = _state(profile)
    message_id = str(uuid.uuid4())
    now = _iso()
    sent = payload.send_now
    message = {
        "id": message_id,
        "event_id": str(payload.event_id),
        "action_id": payload.action_id,
        "subject": subject,
        "body": body,
        "to": _recipient_payload(payload.to),
        "cc": _recipient_payload(payload.cc) if payload.cc else [],
        "importance": payload.importance,
        "due_at": payload.due_at,
        "status": "sent" if sent else "draft",
        "thread_id": message_id,
        "attachment_name": "razbor-sobytiya.pdf" if payload.attach_report else None,
        "reminder_count": 0,
        "created_at": now,
        "updated_at": now,
        "sent_at": now if sent else None,
    }
    messages = _messages(state)
    messages.append(message)
    state["messages"] = messages
    _save(profile, state)
    return _public(message)


def _find(state: dict[str, Any], message_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    messages = _messages(state)
    for message in messages:
        if str(message.get("id")) == message_id:
            return messages, message
    raise OutlookError("Поручение не найдено", status_code=404)


def update_message(
    profile: BusinessProfile,
    message_id: str,
    payload: OutlookMessagePatch,
) -> OutlookMessageOut:
    _require_connected(profile)
    state = _state(profile)
    messages, message = _find(state, message_id)
    if message.get("status") != "draft":
        raise OutlookError("Редактировать можно только черновик", status_code=409)

    if payload.to is not None:
        message["to"] = _recipient_payload(payload.to)
    if payload.cc is not None:
        message["cc"] = _recipient_payload(payload.cc)
    if payload.subject is not None:
        subject = payload.subject.strip()
        if not subject:
            raise OutlookError("Заполните тему письма")
        message["subject"] = subject
    if payload.body is not None:
        body = payload.body.strip()
        if not body:
            raise OutlookError("Заполните текст письма")
        message["body"] = body
    if payload.importance is not None:
        message["importance"] = payload.importance
    if payload.due_at is not None:
        message["due_at"] = payload.due_at
    message["updated_at"] = _iso()
    state["messages"] = messages
    _save(profile, state)
    return _public(message)


def send_message(profile: BusinessProfile, message_id: str) -> OutlookMessageOut:
    _require_connected(profile)
    state = _state(profile)
    messages, message = _find(state, message_id)
    if message.get("status") != "draft":
        raise OutlookError("Письмо уже отправлено", status_code=409)
    now = _iso()
    message["status"] = "sent"
    message["sent_at"] = now
    message["updated_at"] = now
    state["messages"] = messages
    _save(profile, state)
    return _public(message)


def remind(profile: BusinessProfile, message_id: str) -> OutlookMessageOut:
    _require_connected(profile)
    state = _state(profile)
    messages, message = _find(state, message_id)
    status = str(message.get("status"))
    if status == "draft":
        raise OutlookError("Сначала отправьте письмо", status_code=409)
    if status == "replied":
        raise OutlookError("По поручению уже получен ответ", status_code=409)
    now = _iso()
    message["reminder_count"] = int(message.get("reminder_count") or 0) + 1
    message["last_reminder_at"] = now
    message["updated_at"] = now
    state["messages"] = messages
    _save(profile, state)
    return _public(message)


def advance(profile: BusinessProfile, message_id: str) -> OutlookMessageOut:
    """Demo helper: move the message to the next Outlook status."""
    _require_connected(profile)
    state = _state(profile)
    messages, message = _find(state, message_id)
    status = str(message.get("status") or "draft")
    if status == "draft":
        raise OutlookError("Сначала отправьте письмо", status_code=409)
    if status == "replied":
        return _public(message)
    index = STATUS_FLOW.index(status)
    next_status = STATUS_FLOW[min(index + 1, len(STATUS_FLOW) - 1)]
    now = _iso()
    message["status"] = next_status
    message["updated_at"] = now
    if next_status in {"read", "replied"} and not message.get("read_at"):
        message["read_at"] = now
    if next_status == "replied":
        message["replied_at"] = now
    state["messages"] = messages
    _save(profile, state)
    return _public(message)


def delete_message(profile: BusinessProfile, message_id: str) -> None:
    state = _state(profile)
    messages, message = _find(state, message_id)
    if message.get("status") != "draft":
        raise OutlookError("Удалить можно только черновик", status_code=409)
    state["messages"] = [item for item in messages if str(item.get("id")) != message_id]
    _save(profile, state)
