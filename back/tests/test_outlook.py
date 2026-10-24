import uuid

import pytest

from back.db.models import BusinessProfile, Counterparty
from back.schemas.outlook import (
    OutlookConnectRequest,
    OutlookMessageCreate,
    OutlookRecipient,
)
from back.services import outlook


def _profile() -> BusinessProfile:
    return BusinessProfile(
        user_id=uuid.uuid4(),
        entrepreneur_name="Андрей Волков",
        business_name="ТрансМеталл",
        role="cfo",
        outlook_state={},
    )


def _counterparty(index: int, name: str) -> Counterparty:
    return Counterparty(
        company_uid=f"U_{index}",
        direction="supplier" if index % 2 else "buyer",
        total_amount=1_000_000,
        payments_count=10,
        share=0.2,
        importance=8,
        default_name=name,
        note="",
    )


def _payload(send_now: bool = False) -> OutlookMessageCreate:
    return OutlookMessageCreate(
        event_id=uuid.uuid4(),
        action_id="action-1",
        to=[OutlookRecipient(name="Финансовый директор", email="cfo@company.example")],
        subject="Поручение по событию",
        body="Проверьте контракты и сроки.",
        send_now=send_now,
    )


def test_connect_validates_email_and_stores_account() -> None:
    profile = _profile()
    with pytest.raises(outlook.OutlookError):
        outlook.connect(profile, OutlookConnectRequest(email="not-an-email"))

    state = outlook.connect(profile, OutlookConnectRequest(email="owner@company.example"))
    assert state.connected is True
    assert state.email == "owner@company.example"
    assert "Mail.Send" in state.scopes


def test_draft_send_and_status_flow() -> None:
    profile = _profile()
    outlook.connect(profile, OutlookConnectRequest(email="owner@company.example"))

    draft = outlook.create_message(profile, _payload())
    assert draft.status == "draft"
    assert draft.attachment_name == "razbor-sobytiya.pdf"
    assert draft.to[0].email == "cfo@company.example"

    sent = outlook.send_message(profile, draft.id)
    assert sent.status == "sent"
    assert sent.sent_at is not None

    delivered = outlook.advance(profile, draft.id)
    assert delivered.status == "delivered"

    read = outlook.advance(profile, draft.id)
    assert read.status == "read"
    assert read.read_at is not None

    replied = outlook.advance(profile, draft.id)
    assert replied.status == "replied"
    assert replied.replied_at is not None

    with pytest.raises(outlook.OutlookError):
        outlook.remind(profile, draft.id)


def test_send_now_and_reminder() -> None:
    profile = _profile()
    outlook.connect(profile, OutlookConnectRequest(email="owner@company.example"))
    message = outlook.create_message(profile, _payload(send_now=True))
    assert message.status == "sent"

    reminded = outlook.remind(profile, message.id)
    assert reminded.reminder_count == 1
    assert reminded.last_reminder_at is not None

    with pytest.raises(outlook.OutlookError):
        outlook.send_message(profile, message.id)


def test_contacts_include_account_team_and_counterparties() -> None:
    profile = _profile()
    outlook.connect(profile, OutlookConnectRequest(email="owner@company.example"))
    items = outlook.contacts(
        profile,
        [_counterparty(1, "Металл-Снаб"), _counterparty(2, "Завод-Покупатель")],
    )
    emails = {item.email for item in items}
    assert "owner@company.example" in emails
    assert "cfo@company.example" in emails
    assert any(item.name == "Металл-Снаб" for item in items)

    found = outlook.contacts(profile, [], query="бухгалтер")
    assert [item.email for item in found] == ["accountant@company.example"]


def test_disconnect_blocks_new_messages() -> None:
    profile = _profile()
    outlook.connect(profile, OutlookConnectRequest(email="owner@company.example"))
    state = outlook.disconnect(profile)
    assert state.connected is False

    with pytest.raises(outlook.OutlookError):
        outlook.create_message(profile, _payload())
