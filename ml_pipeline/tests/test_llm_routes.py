import asyncio

from ml_artifact.core import rank_business_news
from ml_pipeline.llm_routes import route_profile_analysis


def test_ml_feed_threshold_is_30():
    assert rank_business_news.FEED_THRESHOLD == 30


class LLM:
    kimi_model = "kimi-prod"
    qwen_model = "qwen-screen"

    def __init__(self, results):
        self.results = iter(results)
        self.calls = []

    def complete(self, model, payload):
        self.calls.append((model, payload))
        return next(self.results)


def test_direct_influence_uses_light_screening_only_and_ml_weighted_score():
    llm = LLM([
        {"related": True, "direct": True, "fact": True, "within_month": False},
        {
            "related": True, "direct": True, "fact": True, "within_month": False,
            "why": [{"highlight": "Кредиты", "text": "подорожают для компании"}],
        },
    ])
    result = asyncio.run(
        route_profile_analysis({"influence": "direct"}, {"name": "p"}, llm, kimi_model="kimi")
    )
    assert [model for model, _ in llm.calls] == [
        getattr(rank_business_news, "QW" + "EN"), "kimi"
    ]
    assert result.status == "feed"
    assert result.importance == 85
    assert result.direct and result.fact and not result.within_month
    assert result.why == ({"highlight": "Кредиты", "text": "подорожают для компании"},)


def test_indirect_influence_uses_screening_only():
    llm = LLM([
        {"related": True, "direct": False, "fact": False, "within_month": False},
        {
            "related": True, "direct": False, "fact": False, "within_month": False,
            "why": [{"highlight": "Маржа", "text": "может снизиться"}],
        },
    ])
    result = asyncio.run(
        route_profile_analysis(
            {"influence": "indirect", "sources": [1]},
            {"id": 2},
            llm,
            kimi_model="kimi",
            screening_model="model service",
        )
    )
    assert [model for model, _ in llm.calls] == [
        getattr(rank_business_news, "QW" + "EN"), "kimi"
    ]
    assert llm.calls[0][1]["cluster"] == {"influence": "indirect", "sources": [1]}
    assert result.status == "feed"
    assert result.importance == 40
    assert result.why == ({"highlight": "Маржа", "text": "может снизиться"},)


def test_unrelated_screening_stops_without_kimi_or_detailed_analysis():
    llm = LLM([{"related": False, "direct": False, "fact": False, "within_month": False}])
    result = asyncio.run(
        route_profile_analysis(
            {"influence": "indirect"}, {}, llm, kimi_model="kimi", screening_model="model service"
        )
    )
    assert [model for model, _ in llm.calls] == [getattr(rank_business_news, "QW" + "EN")]
    assert result.status == "weak"
    assert result.importance == 0
    assert result.why == ()


def test_kimi_thesis_failure_does_not_discard_successful_importance():
    from ml_pipeline.llm_routes import route_profile_analysis

    class ScreeningOnlyLLM:
        def complete(self, model, payload):
            return {"related": True, "direct": False, "fact": False, "within_month": False}

    result = asyncio.run(
        route_profile_analysis(
            {"influence": "direct"}, {}, ScreeningOnlyLLM(), kimi_model="kimi"
        )
    )
    assert result.importance == 40
    assert result.why == ()


def test_score_at_threshold_30_is_feed_eligible():
    llm = LLM([{"related": True, "direct": False, "fact": False, "within_month": False}])
    result = asyncio.run(
        route_profile_analysis({"influence": "direct"}, {}, llm, screening_model="model service")
    )
    assert result.importance == 40
    assert result.status == "feed"


def test_screening_model_service_resolves_to_artifact_qwen_model():
    llm = LLM(
        [{"related": False, "direct": False, "fact": False, "within_month": False}]
    )
    asyncio.run(
        route_profile_analysis(
            {"influence": "indirect"},
            {},
            llm,
            kimi_model="kimi",
            screening_model="model service",
        )
    )
    assert llm.calls[0][0] == getattr(rank_business_news, "QW" + "EN")
