from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from back.schemas.common import ORMModel


class RegisterRequest(BaseModel):
    login: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    login: str
    password: str


class UserOut(ORMModel):
    id: UUID
    login: str
    is_active: bool
    created_at: datetime


class OnboardingBrief(BaseModel):
    completed: bool
    next_step: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    onboarding: OnboardingBrief
