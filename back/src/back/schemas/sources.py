from typing import Any

from pydantic import BaseModel, Field


class ChannelOut(BaseModel):
    id: str
    name: str
    handle: str | None = None
    topics: str
    kind: str = "catalog"
    subscribed: bool = False
    recommended: bool = False
    avatar_url: str | None = None
    feed_url: str | None = None
    source_type: str = "telegram"
    tg_subscribers: int | None = None
    popularity: int | None = None
    category_ids: list[int] = []


class SourcesState(BaseModel):
    channels: list[ChannelOut]
    alfa_analytics: bool = True
    recommended_count: int
    custom_count: int
    catalog_total: int


class ChannelCatalogResponse(BaseModel):
    query: str
    items: list[ChannelOut]
    total: int


class ChannelAddRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)


class NotificationSettings(BaseModel):
    settings: dict[str, Any]
