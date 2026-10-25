from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IngestPostRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    text: str = Field(default="", description="Raw post body; title is derived when empty")
    title: str | None = None
    source: str | None = None
    source_name: str | None = None
    channel: str | None = None
    url: str | None = None
    published_at: str | datetime | None = None
    profile_id: UUID | None = Field(
        default=None, description="Optional demo profile for per-profile influence and tracked"
    )


class IngestPostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    text: str
    source_name: str | None
    url: str | None
    published_at: datetime
    categories: list[int]
    cluster_key: str | None
    news_event_id: UUID | None
    tracked_item_id: UUID | None
    importance: int | None
    similarity: float | None
    status: str
    stage: str
    decision_trace: list[dict[str, Any]]
    created_at: datetime


class IngestPostTrace(IngestPostOut):
    raw: dict[str, Any]
    parsed: dict[str, Any]
    embedding: list[float]


class IngestChannelOut(BaseModel):
    id: str
    name: str
    handle: str
    subscribers: int


class IngestChannelList(BaseModel):
    items: list[IngestChannelOut]
