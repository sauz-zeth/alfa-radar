from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SourcePostOut(BaseModel):
    name: str
    time: datetime
    tone: str = "neutral"
    text: str
    is_primary: bool = False
    handle: str | None = None
    url: str | None = None
    image_url: str | None = None


class ScoreComponentOut(BaseModel):
    key: str
    label: str
    value: int
    max: int = 5
    text: str


class SourceComparisonOut(BaseModel):
    agree: list[str] = []
    differ: list[str] = []
    single: list[str] = []


class ThesisOut(BaseModel):
    category: str
    text: str
    status: str
    sources: list[str] = []


class AlfaAnalyticsOut(BaseModel):
    author: str
    text: str


class ScenarioOut(BaseModel):
    name: str
    effect: float
    effect_label: str
    probability: int
    note: str
    formula: str


class AssumptionOut(BaseModel):
    key: str
    label: str
    effect: str


class ScenarioSetOut(BaseModel):
    horizon: str
    horizon_label: str
    lever_label: str
    lever_values: list[str]
    scenarios: list[ScenarioOut]
    assumptions: list[AssumptionOut]
    note: str
    needs_profile: list[str] = []


class QuestionOut(BaseModel):
    id: str
    text: str
    status: str
    answer: str | None = None
    source: str | None = None
    date: str | None = None
    internal: bool = False


class TimelinePointOut(BaseModel):
    date: str
    text: str
    importance: int
    is_current: bool = False


class ActionOut(BaseModel):
    title: str
    role: str
    deadline: str
    origin: str = "AI"


class AgentStepOut(BaseModel):
    type: str
    text: str


class ChatMessageOut(BaseModel):
    question: str
    answer: str
    origin: str = "AI"


class ProductOut(BaseModel):
    name: str
    description: str
    benefit: str


class InsightOut(BaseModel):
    sources: list[SourcePostOut]
    score_breakdown: list[ScoreComponentOut]
    score_why: str
    impact_share: str
    comparison: SourceComparisonOut
    theses: list[ThesisOut]
    alfa: AlfaAnalyticsOut | None = None
    scenarios: ScenarioSetOut
    open_questions: list[QuestionOut]
    timeline: list[TimelinePointOut]
    checklist: list[str]
    actions: list[ActionOut]
    agent_log: list[AgentStepOut]
    product: ProductOut | None = None
    chat: list[ChatMessageOut] = []
    facts: list[dict[str, Any]] = []
