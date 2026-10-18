import json
from collections.abc import Mapping
from dataclasses import dataclass

from back.ml.llm import LLMClient
from back.pipeline.rank import importance
from back.schemas.llm import ChainReport

SYSTEM_PROMPT = (
    "Ты аналитик, который обновляет отчёт по отслеживаемой истории для конкретной компании. "
    "Пиши только разницу с прошлым отчётом, коротко и по делу. Ответ — строгий JSON."
)


@dataclass(frozen=True, slots=True)
class ChainReportResult:
    change: str
    conclusions_changed: bool
    materiality: int
    certainty: int
    impact: str
    actions: list[str]
    importance: float


class ChainReporter:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def report(
        self,
        profile: Mapping[str, object],
        previous_report: str,
        event_title: str,
        what_changed: str,
    ) -> ChainReportResult:
        payload = {
            "company_profile": profile,
            "previous_report": previous_report,
            "new_event": event_title,
            "what_changed": what_changed,
        }
        user_prompt = (
            "Верни JSON: change (2-3 предложения, что изменилось для компании), "
            "conclusions_changed (bool), materiality (1-5), certainty (1-5), "
            "impact (risk | opportunity), actions (список строк).\n\n"
            f"Данные:\n{json.dumps(payload, ensure_ascii=False)}"
        )
        response: ChainReport = await self._llm.complete_json(
            SYSTEM_PROMPT,
            user_prompt,
            ChainReport,
        )
        return ChainReportResult(
            change=response.change,
            conclusions_changed=response.conclusions_changed,
            materiality=response.materiality,
            certainty=response.certainty,
            impact=response.impact.value,
            actions=list(response.actions),
            importance=importance(response.materiality, response.certainty),
        )
