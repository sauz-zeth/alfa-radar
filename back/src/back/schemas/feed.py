from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from back.schemas.common import ORMModel


class CategoryBrief(BaseModel):
    id: int
    name: str
    short_name: str


class FeedItem(BaseModel):
    id: UUID
    title: str
    summary: str
    what_it_means: str
    source_name: str
    source_url: str | None = None
    published_at: datetime
    impact: str
    impact_label: str
    importance: int
    categories: list[CategoryBrief]
    matched_categories: list[CategoryBrief]
    matched_counterparties: list[str]
    match_reason: str
    is_tracked: bool
    prognosis_note: str
    detail_note: str


class FeedItemDetail(FeedItem):
    facts: list[dict[str, Any]] = []


class FeedbackRequest(BaseModel):
    action: Literal["track", "skip", "important", "not_relevant"]


class TrackedItemOut(ORMModel):
    id: UUID
    event_id: UUID
    status: str
    report: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    event: FeedItem


class TrackedListResponse(BaseModel):
    items: list[TrackedItemOut]
    total: int


class AgentReanalyzeRequest(BaseModel):
    question: str | None = Field(default=None, max_length=1000)
