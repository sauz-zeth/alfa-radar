from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class FeedCard(BaseModel):
    event_id: int
    title: str
    why: str
    impact: str
    importance: float
    t0: datetime
    n_src: int
    main_category: str | None = None
    chain_id: int | None = None


class EventDetail(BaseModel):
    event_id: int
    title: str
    why: str | None = None
    impact: str | None = None
    importance: float | None = None
    materiality: int | None = None
    certainty: int | None = None
    horizon: str | None = None
    t0: datetime
    n_src: int
    categories: dict[str, float] = Field(default_factory=dict)
    mentions: list[str] = Field(default_factory=list)


class Factor(BaseModel):
    category: str
    w: float = Field(ge=0.0, le=1.0)
    why: str = ""


class Entity(BaseModel):
    name: str
    role: Literal["self", "client", "supplier", "competitor", "region"]
    aliases: list[str] = Field(default_factory=list)


class CompanyProfilePayload(BaseModel):
    description: str = ""
    factors: list[Factor] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)


class SwipeRequest(BaseModel):
    user_id: int
    event_id: int
    direction: Literal["left", "right"]
    reason: Literal["not_interesting", "bad_feed", "irrelevant", "seen"] | None = None


class ChainView(BaseModel):
    chain_id: int
    summary: str
    status: str
    last_update: datetime
    subscribed: bool = False


class ChainReportView(BaseModel):
    report_id: int
    chain_id: int
    event_id: int
    change: str
    conclusions_changed: bool
    importance: float
    impact: str
    actions: list[str] = Field(default_factory=list)
    created_at: datetime
