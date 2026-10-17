from typing import TypeVar

import litellm
from pydantic import BaseModel, ValidationError

from back.config import settings

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class LLMClient:
    def __init__(
        self,
        model: str | None = None,
        fast_model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        retries: int | None = None,
    ) -> None:
        self._model = model or settings.llm_model
        self._fast_model = fast_model or settings.llm_fast_model
        self._base_url = base_url or settings.litellm_base_url
        self._api_key = api_key or settings.litellm_api_key
        self._retries = settings.llm_retries if retries is None else retries

    async def complete_json(
        self,
        system: str,
        user: str,
        schema: type[SchemaT],
        fast: bool = False,
    ) -> SchemaT:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        last_error: Exception | None = None
        for _ in range(self._retries + 1):
            response = await litellm.acompletion(
                model=self._fast_model if fast else self._model,
                messages=messages,
                api_base=self._base_url,
                api_key=self._api_key,
                timeout=settings.llm_timeout,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or ""
            try:
                return schema.model_validate_json(content)
            except (ValidationError, ValueError) as error:
                last_error = error
                messages.append({"role": "assistant", "content": content})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"Ответ не соответствует схеме {schema.__name__}: {error}. "
                            "Верни только исправленный JSON."
                        ),
                    }
                )
        raise ValueError(f"LLM не вернула валидный {schema.__name__}") from last_error
