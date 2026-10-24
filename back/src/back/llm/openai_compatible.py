import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from back.config import Settings
from back.llm.base import BaseLLM, LLMBudgetExceeded, LLMError

logger = logging.getLogger(__name__)


class OpenAICompatibleLLM(BaseLLM):
    provider_name = "openai"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = settings.llm_base_url.rstrip("/")
        self._api_key = settings.llm_api_key

    async def complete_text(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        temperature: float | None = None,
    ) -> str:
        if not self._api_key:
            raise LLMError("LLM_API_KEY is not configured")

        payload: dict[str, Any] = {
            "model": model or self._settings.llm_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": (self._settings.llm_temperature if temperature is None else temperature),
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self._base_url}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=self._settings.llm_timeout_seconds) as client:
                response = await client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise LLMError(f"LLM request failed: {exc}") from exc

        if response.status_code in {402, 429}:
            raise LLMBudgetExceeded(response.text[:500])
        if response.status_code >= 400:
            raise LLMError(f"LLM returned {response.status_code}: {response.text[:500]}")

        try:
            data = response.json()
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMError(f"Unexpected LLM response: {response.text[:500]}") from exc

    async def stream_text(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        if not self._api_key:
            raise LLMError("LLM_API_KEY is not configured")

        payload: dict[str, Any] = {
            "model": model or self._settings.llm_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": (self._settings.llm_temperature if temperature is None else temperature),
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        url = f"{self._base_url}/chat/completions"

        try:
            async with (
                httpx.AsyncClient(timeout=self._settings.llm_timeout_seconds) as client,
                client.stream("POST", url, json=payload, headers=headers) as response,
            ):
                if response.status_code >= 400:
                    body = (await response.aread()).decode("utf-8", "replace")
                    if response.status_code in {402, 429}:
                        raise LLMBudgetExceeded(body[:500])
                    raise LLMError(f"LLM returned {response.status_code}: {body[:500]}")
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    content = (choices[0].get("delta") or {}).get("content")
                    if content:
                        yield str(content)
        except httpx.HTTPError as exc:
            raise LLMError(f"LLM request failed: {exc}") from exc
