from typing import Any

from pydantic import BaseModel

from back.schemas.onboarding import CategoryOut, CounterpartyOut, ProfileOut


class ProfileBundle(BaseModel):
    profile: ProfileOut
    categories: list[CategoryOut]
    counterparties: list[CounterpartyOut]
    reporting: dict[str, Any]
