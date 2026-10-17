import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from back.ml.llm import LLMClient
from back.schemas.llm import ChainMatch

SYSTEM_PROMPT = (
    "Ты проверяешь, продолжает ли новое событие одну из отслеживаемых историй. "
    "Продолжение должно содержать новый факт, а не перепечатку, мнение или пересказ. "
    "При сомнении возвращай chain_id = null. Ответ — строгий JSON."
)


@dataclass(frozen=True, slots=True)
class ChainDecision:
    chain_id: int
    what_changed: str


class ChainMatcher:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def match(
        self,
        event_title: str,
        sources: Sequence[str],
        t0: str,
        candidates: Mapping[int, str],
    ) -> ChainDecision | None:
        payload = {
            "event": {"title": event_title, "sources": list(sources[:3]), "t0": t0},
            "candidates": [
                {"chain_id": str(chain_id), "summary": summary}
                for chain_id, summary in candidates.items()
            ],
        }
        user_prompt = (
            "Верни JSON: chain_id (строка из candidates или null), "
            "has_new_fact (bool), what_changed (одна фраза).\n\n"
            f"Данные:\n{json.dumps(payload, ensure_ascii=False)}"
        )
        response: ChainMatch = await self._llm.complete_json(
            SYSTEM_PROMPT,
            user_prompt,
            ChainMatch,
            fast=True,
        )
        if response.chain_id is None or not response.has_new_fact:
            return None
        try:
            chain_id = int(response.chain_id)
        except ValueError:
            return None
        if chain_id not in candidates:
            return None
        return ChainDecision(chain_id=chain_id, what_changed=response.what_changed)
