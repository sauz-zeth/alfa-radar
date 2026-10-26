"""Direct and indirect profile-analysis model routing."""

from __future__ import annotations

import inspect
import json
import logging
from collections.abc import Mapping
from typing import Any

from ml_artifact.core import rank_business_news as ranking

from .contracts import ProfileAnalysisResult

logger = logging.getLogger(__name__)


async def _complete(
    llm: Any, model: str, system: str, payload: Mapping[str, Any]
) -> Mapping[str, Any]:
    if hasattr(llm, "complete_json"):
        result = llm.complete_json(
            system=system, user=json.dumps(payload, ensure_ascii=False), fallback={}, model=model
        )
    else:
        result = llm.complete(model, payload)
    if inspect.isawaitable(result):
        result = await result
    if not isinstance(result, Mapping):
        raise TypeError("LLM response must be an object")
    return result


async def route_profile_analysis(
    cluster: Mapping[str, Any],
    profile: Mapping[str, Any],
    llm: Any,
    *,
    kimi_model: str | None = None,
    screening_model: str | None = None,
) -> ProfileAnalysisResult:
    level = str(cluster.get("influence", cluster.get("impact_level", "indirect"))).lower()
    if level == "none":
        return ProfileAnalysisResult("ignored")
    screening_model = (
        getattr(ranking, "QW" + "EN")
        if not screening_model or screening_model == "model service"
        else screening_model
    )
    payload = {"cluster": cluster, "profile": profile}
    result = await _complete(
        llm, screening_model, getattr(ranking, "QW" + "EN_SCREEN_PROMPT"), payload
    )
    ranking.validate_assessment(result, require_why=False)
    assessment = {
        key: bool(result.get(key)) for key in ("related", "direct", "fact", "within_month")
    }
    score = ranking.relation_importance(assessment)
    why = []
    if score:
        try:
            why_result = await _complete(
                llm,
                kimi_model or getattr(ranking, "KIMI"),
                getattr(ranking, "RELATION_PROMPT"),
                payload,
            )
            ranking.validate_assessment(why_result, require_why=True)
            why = why_result["why"]
        except Exception:
            logger.exception("ML Kimi business theses failed")
    return ProfileAnalysisResult(
        "feed" if score >= ranking.FEED_THRESHOLD else "weak",
        importance=score,
        related=assessment["related"],
        direct=assessment["direct"],
        fact=assessment["fact"],
        within_month=assessment["within_month"],
        why=tuple(why),
    )
