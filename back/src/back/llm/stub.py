from typing import Any

from back.llm.base import BaseLLM


class StubLLM(BaseLLM):
    """Offline provider.

    It does not invent data. Every caller passes a deterministic fallback that is
    computed from the business profile / payments / reporting text. This keeps the
    whole product usable without an API key while the LLM layer stays replaceable.
    """

    provider_name = "stub"

    async def complete_text(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        temperature: float | None = None,
    ) -> str:
        return ""

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        fallback: dict[str, Any] | None = None,
        model: str | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        return fallback or {}
