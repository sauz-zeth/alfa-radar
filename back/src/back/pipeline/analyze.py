import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from back.ml.llm import LLMClient
from back.pipeline.rank import importance
from back.schemas.llm import LLMAnalysis

SYSTEM_PROMPT = (
    "Ты аналитик новостей для руководителя компании. Оценивай только влияние события "
    "на выручку и затраты этой компании. Верни строгий JSON без пояснений."
)


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    materiality: int
    certainty: int
    horizon: str
    impact: str
    why: str
    importance: float


class EventAnalyzer:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def analyze(
        self,
        event_title: str,
        sources: Sequence[str],
        profile: Mapping[str, object],
        fired: Sequence[str],
        mentions: Sequence[str],
    ) -> AnalysisResult:
        payload = {
            "event": {"title": event_title, "sources": list(sources[:3])},
            "company_profile": profile,
            "triggered_categories": list(fired),
            "mentions": list(mentions),
        }
        user_prompt = (
            "Оцени событие по шкалам. Поля ответа:\n"
            "materiality: 1-5, влияние на выручку или затраты;\n"
            "certainty: 1-5, 5 — событие состоялось и подтверждено;\n"
            "horizon: hours | days | weeks;\n"
            "impact: risk | opportunity;\n"
            "why: одна короткая фраза, почему это важно.\n\n"
            f"Данные:\n{json.dumps(payload, ensure_ascii=False)}"
        )
        response: LLMAnalysis = await self._llm.complete_json(
            SYSTEM_PROMPT,
            user_prompt,
            LLMAnalysis,
        )
        return AnalysisResult(
            materiality=response.materiality,
            certainty=response.certainty,
            horizon=response.horizon.value,
            impact=response.impact.value,
            why=response.why,
            importance=importance(response.materiality, response.certainty),
        )
