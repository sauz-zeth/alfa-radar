from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from back.schemas.common import ORMModel
from back.schemas.insights import (
    ImpactMetricOut,
    InsightOut,
    QuestionOut,
    ScoreComponentOut,
    SourcePostOut,
)


class FeedbackOut(BaseModel):
    action: str
    reason: str | None = None
    created_at: datetime


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
    is_liked: bool = False
    likes: int = 0
    source_count: int = 1
    sources: list[SourcePostOut] = []
    facts: list[dict[str, Any]] = []
    impact_metrics: list[ImpactMetricOut] = []
    score_breakdown: list[ScoreComponentOut] = []
    score_why: str = ""
    impact_share: str = ""
    is_important_mention: bool = False
    chain_key: str | None = None
    update_label: str | None = None
    changed_at: datetime | None = None
    conclusions_changed: bool = False
    feedback: FeedbackOut | None = None
    prognosis_note: str
    detail_note: str


class FeedItemDetail(FeedItem, InsightOut):
    pass


class FeedbackRequest(BaseModel):
    action: Literal[
        "track",
        "skip",
        "important",
        "not_relevant",
        "fact_error",
        "score_inaccurate",
    ]
    reason: str | None = Field(default=None, max_length=255)


class HiddenItem(BaseModel):
    id: UUID
    title: str
    impact: str
    impact_label: str
    importance: int
    reason: str
    age_days: int
    expires_in_days: int
    published_at: datetime
    source_name: str
    action: str


class HiddenTab(BaseModel):
    key: str
    label: str
    count: int


class HiddenResponse(BaseModel):
    tab: str
    description: str
    total: int
    tabs: list[HiddenTab]
    items: list[HiddenItem]


class LikeResponse(BaseModel):
    liked: bool
    likes: int


class TrackedEventOut(BaseModel):
    event_id: UUID
    title: str
    what_changed: str | None = None
    importance: int
    impact: str
    impact_label: str
    published_at: datetime


class TrackedItemOut(ORMModel):
    id: UUID
    event_id: UUID
    status: Literal["active", "archived"]
    title: str | None = None
    what_changed: str | None = None
    conclusions_changed: bool = False
    questions: list[QuestionOut] = []
    report: dict[str, Any]
    analysis_pending: bool = False
    created_at: datetime
    updated_at: datetime
    event: FeedItem
    events: list[TrackedEventOut] = []
    insight: InsightOut | None = None


class TrackedListResponse(BaseModel):
    items: list[TrackedItemOut]
    total: int


class FeedQuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class TrackToggleResponse(BaseModel):
    is_tracked: bool


class AgentReanalyzeRequest(BaseModel):
    question: str | None = Field(default=None, max_length=1000)


class TrackedQuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
