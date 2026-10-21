from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from back.core.constants import Role
from back.schemas.business import BusinessOut
from back.schemas.common import ORMModel


class CategoryOut(BaseModel):
    category_id: int
    slug: str
    name: str
    short_name: str
    group: str
    description: str
    example: str
    channels: list[str]
    weight: float
    rationale: str
    is_manual: bool


class CounterpartyOut(ORMModel):
    id: UUID
    company_uid: str | None = None
    direction: str
    total_amount: float
    payments_count: int
    share: float
    importance: int
    default_name: str
    custom_name: str | None = None
    display_name: str
    note: str


class CounterpartyRenameRequest(BaseModel):
    name: str | None = Field(default=None, max_length=128)


class CounterpartyRenameItem(BaseModel):
    id: UUID
    name: str | None = None


class CounterpartyRenameBatch(BaseModel):
    items: list[CounterpartyRenameItem]


class ProfileOut(ORMModel):
    id: UUID
    user_id: UUID
    company_uid: str | None = None
    entrepreneur_name: str
    business_name: str
    role: str | None = None
    role_label: str | None = None
    tags: list[str] = []
    onboarding_step: str
    onboarding_completed: bool
    reporting_summary: dict[str, Any] = {}
    company: BusinessOut | None = None


class ProfileUpdateRequest(BaseModel):
    entrepreneur_name: str | None = Field(default=None, max_length=128)
    business_name: str | None = Field(default=None, max_length=255)
    role: Role | None = None


class RoleRequest(BaseModel):
    role: Role


class CategoryWeightRequest(BaseModel):
    weight: float = Field(ge=0, le=1)


class OnboardingStepState(BaseModel):
    key: str
    title: str
    done: bool
    optional: bool = False


class OnboardingState(BaseModel):
    completed: bool
    next_step: str
    steps: list[OnboardingStepState]
    profile: ProfileOut | None = None


class ReportingUploadOut(ORMModel):
    id: UUID
    form_type: str
    filename: str
    content_type: str | None = None
    extracted: dict[str, Any]
    status: str


class ReportingResponse(BaseModel):
    uploads: list[ReportingUploadOut]
    summary: dict[str, Any]
    accepted_forms: list[str]


class SkipStepRequest(BaseModel):
    step: str
