from typing import Any

from pydantic import BaseModel

from back.schemas.onboarding import CategoryOut, CounterpartyOut, ProfileOut


class ProfileStatsOut(BaseModel):
    industry: str | None = None
    city: str | None = None
    region: str | None = None
    revenue: float | None = None
    revenue_label: str
    revenue_segment: str | None = None
    employees: str | None = None
    age: str | None = None
    foreign_trade_country: str | None = None
    products: list[str] = []
    tags: list[str] = []


class CategoryGroupOut(BaseModel):
    key: str
    name: str
    description: str
    weight_min: float
    weight_max: float
    items: list[CategoryOut]


class NotificationTriggerOut(BaseModel):
    key: str
    label: str
    channel: str
    enabled: bool = True


class ProfileBundle(BaseModel):
    profile: ProfileOut
    stats: ProfileStatsOut
    category_groups: list[CategoryGroupOut]
    categories: list[CategoryOut]
    counterparties: list[CounterpartyOut]
    counterparties_by_direction: dict[str, list[CounterpartyOut]] = {}
    notifications: list[NotificationTriggerOut] = []
    reporting: dict[str, Any]
