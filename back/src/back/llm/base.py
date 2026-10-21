import json
import re
from abc import ABC, abstractmethod
from typing import Any


class LLMError(RuntimeError):
    pass


class LLMBudgetExceeded(LLMError):
    pass


def parse_json_response(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise LLMError("LLM response is not valid JSON") from None
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise LLMError("LLM response must be a JSON object")
    return value


class BaseLLM(ABC):
    provider_name = "base"

    @abstractmethod
    async def complete_text(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        temperature: float | None = None,
    ) -> str:
        raise NotImplementedError

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        fallback: dict[str, Any] | None = None,
        model: str | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        try:
            text = await self.complete_text(
                system=system,
                user=user,
                model=model,
                temperature=temperature,
            )
            return parse_json_response(text)
        except LLMError:
            if fallback is None:
                raise
            return fallback
