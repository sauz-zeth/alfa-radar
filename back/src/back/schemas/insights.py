from datetime import datetime
from typing import Any, Literal

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
    status: str = "single"
    status_label: str = "Один канал"


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
    share: str | None = None
    origin: str | None = None
    is_base: bool = False


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
    forecast_note: str | None = None


class QuestionOut(BaseModel):
    id: str
    text: str
    status: str
    status_code: str = "waiting"
    answer: str | None = None
    source: str | None = None
    date: str | None = None
    internal: bool = False


class TimelinePointOut(BaseModel):
    date: str
    text: str
    importance: int
    is_current: bool = False


class ImpactMetricOut(BaseModel):
    key: str | None = None
    label: str
    value: str
    previous_value: str | None = None
    unit: str | None = None
    note: str = ""
    tone: str | None = None


class ActionOut(BaseModel):
    title: str
    role: str
    deadline: str
    origin: str = "AI"
    id: str | None = None
    description: str | None = None
    deadline_label: str | None = None
    is_primary: bool = False


class AgentStepOut(BaseModel):
    type: str
    text: str
    is_correction: bool = False
    at: str | None = None


class ImpactTileOut(BaseModel):
    type: Literal["metric", "statement", "accent"]
    value: str | None = None
    label: str
    note: str | None = None
    span: Literal["half", "full"] = "half"


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
    impact_tiles: list[ImpactTileOut] = []
    scenarios: ScenarioSetOut
    open_questions: list[QuestionOut]
    timeline: list[TimelinePointOut]
    checklist: list[str]
    actions: list[ActionOut]
    agent_log: list[AgentStepOut]
    product: ProductOut | None = None
    chat: list[ChatMessageOut] = []
    facts: list[dict[str, Any]] = []
    questions_answered: int = 0
    questions_waiting: int = 0
    timeline_total: int = 0
    timeline_current_index: int = 0
    analysis_finished_at: str | None = None
    analysis_pending: bool = False
