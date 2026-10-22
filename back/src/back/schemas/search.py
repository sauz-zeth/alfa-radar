from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SearchCompanyOut(BaseModel):
    uid: str
    name: str
    role: str
    city: str | None = None
    region: str | None = None
    okved: str | None = None
    revenue: float | None = None
    revenue_segment: str
    initials: str


class SearchNewsOut(BaseModel):
    id: UUID
    title: str
    summary: str
    impact: str
    impact_label: str
    importance: int
    published_at: datetime
    source_name: str
    is_hidden: bool = False
    is_tracked: bool = False


class SearchResponse(BaseModel):
    query: str
    companies: list[SearchCompanyOut]
    news: list[SearchNewsOut]
    total_companies: int
    total_news: int


class SearchHistoryItem(BaseModel):
    id: str
    query: str
    created_at: datetime


class SearchHistoryResponse(BaseModel):
    items: list[SearchHistoryItem]
