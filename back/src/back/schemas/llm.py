from enum import StrEnum

from pydantic import BaseModel, Field


class Horizon(StrEnum):
    hours = "hours"
    days = "days"
    weeks = "weeks"


class Impact(StrEnum):
    risk = "risk"
    opportunity = "opportunity"


class LLMAnalysis(BaseModel):
    materiality: int = Field(ge=1, le=5)
    certainty: int = Field(ge=1, le=5)
    horizon: Horizon
    impact: Impact
    why: str = Field(min_length=1, max_length=500)


class ChainMatch(BaseModel):
    chain_id: str | None = None
    has_new_fact: bool
    what_changed: str = Field(default="", max_length=500)


class ChainReport(BaseModel):
    change: str = Field(min_length=1, max_length=2000)
    conclusions_changed: bool
    materiality: int = Field(ge=1, le=5)
    certainty: int = Field(ge=1, le=5)
    impact: Impact
    actions: list[str] = Field(default_factory=list)
