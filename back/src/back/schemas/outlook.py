from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

OutlookStatus = Literal["draft", "sent", "delivered", "read", "replied"]
OutlookImportance = Literal["normal", "high"]


class OutlookRecipient(BaseModel):
    name: str = Field(default="", max_length=128)
    email: str = Field(min_length=3, max_length=255)


class OutlookContact(BaseModel):
    name: str
    email: str
    role: str
    source: str


class OutlookContactList(BaseModel):
    items: list[OutlookContact]


class OutlookMessageOut(BaseModel):
    id: str
    event_id: str
    action_id: str | None = None
    subject: str
    body: str
    to: list[OutlookRecipient]
    cc: list[OutlookRecipient] = []
    importance: OutlookImportance = "normal"
    due_at: str | None = None
    status: OutlookStatus
    status_label: str
    thread_id: str
    attachment_name: str | None = None
    reminder_count: int = 0
    created_at: str
    updated_at: str
    sent_at: str | None = None
    read_at: str | None = None
    replied_at: str | None = None
    last_reminder_at: str | None = None


class OutlookStateOut(BaseModel):
    connected: bool
    provider: str = "mock"
    email: str | None = None
    scopes: list[str] = []
    demo: bool = True
    messages: list[OutlookMessageOut] = []


class OutlookConnectRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)


class OutlookMessageCreate(BaseModel):
    event_id: UUID
    action_id: str | None = Field(default=None, max_length=128)
    to: list[OutlookRecipient] = Field(min_length=1)
    cc: list[OutlookRecipient] = []
    subject: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=20000)
    importance: OutlookImportance = "normal"
    due_at: str | None = Field(default=None, max_length=64)
    attach_report: bool = True
    send_now: bool = False


class OutlookMessagePatch(BaseModel):
    to: list[OutlookRecipient] | None = None
    cc: list[OutlookRecipient] | None = None
    subject: str | None = Field(default=None, min_length=1, max_length=255)
    body: str | None = Field(default=None, min_length=1, max_length=20000)
    importance: OutlookImportance | None = None
    due_at: str | None = Field(default=None, max_length=64)
