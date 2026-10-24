from datetime import UTC, datetime
from uuid import uuid4

import pytest

from back.config import get_settings
from back.services.ml import StubPostClassifier, cosine
from back.services.parsing import parse_post, parse_published_at
from back.services.pipeline import (
    DIRECT,
    FEED_IMPORTANCE_THRESHOLD,
    INDIRECT,
    NONE,
    ClusterCandidate,
    continue_theme,
    decide_importance,
    fallback_importance,
    influence_level,
    resolve_cluster,
    route_post,
)


def test_parse_cleans_markup_and_derives_title() -> None:
    parsed = parse_post(
        {
            "text": "<p>ЦБ&nbsp;повысил <b>ключевую</b> ставку до 21%.</p>"
            "<script>alert(1)</script> Подробности позже.",
            "source_name": "ЦБ РФ",
            "published_at": "24.10.2026",
        }
    )
    assert parsed.text == "ЦБ повысил ключевую ставку до 21%. alert(1) Подробности позже."
    assert parsed.title == "ЦБ повысил ключевую ставку до 21%."
    assert parsed.source_name == "ЦБ РФ"
    assert parsed.published_at == datetime(2026, 10, 24, tzinfo=UTC)


def test_parse_accepts_title_only_and_iso_z() -> None:
    parsed = parse_post({"title": "Новость без текста", "published_at": "2026-10-24T10:00:00Z"})
    assert parsed.text == "Новость без текста"
    assert parsed.title == "Новость без текста"
    assert parsed.source_name == "Неизвестный источник"
    assert parsed.published_at == datetime(2026, 10, 24, 10, 0, tzinfo=UTC)


def test_parse_human_date_and_rejects_empty() -> None:
    assert parse_published_at("24 октября 2026") == datetime(2026, 10, 24, tzinfo=UTC)
    assert parse_published_at(None).tzinfo is not None
    with pytest.raises(ValueError):
        parse_post({"text": "  <b> </b> "})


async def test_classifier_is_deterministic() -> None:
    classifier = StubPostClassifier()
    first = await classifier.classify(
        "ЦБ повысил ключевую ставку", "Регулятор ужесточил ДКП и ставку."
    )
    second = await classifier.classify(
        "ЦБ повысил ключевую ставку", "Регулятор ужесточил ДКП и ставку."
    )
    assert 1 in first.categories
    assert 1 in second.categories
    assert first.embedding == second.embedding
    assert len(first.embedding) == 64
    assert cosine(first.embedding, second.embedding) == pytest.approx(1.0)


async def test_cluster_high_similarity_is_source_without_weak_model() -> None:
    async def forbidden(left: str, right: str) -> bool:
        raise AssertionError("weak model must not be called for >= 0.85")

    candidate = ClusterCandidate("cluster-1", 0.9, "same event", uuid4())
    result = await resolve_cluster("new text", [candidate], forbidden)
    assert result.decision == "source_cluster"
    assert result.cluster_key == "cluster-1"
    assert result.news_event_id == candidate.news_event_id
    assert result.similarity == 0.9


async def test_cluster_ambiguous_yes_and_no() -> None:
    candidate = ClusterCandidate("cluster-2", 0.8, "same event", uuid4())

    async def yes(left: str, right: str) -> bool:
        return True

    async def no(left: str, right: str) -> bool:
        return False

    same = await resolve_cluster("new text", [candidate], yes)
    assert same.decision == "source_cluster"
    assert same.cluster_key == "cluster-2"

    different = await resolve_cluster("new text", [candidate], no)
    assert different.decision == "new_cluster"
    assert different.cluster_key != "cluster-2"
    assert different.news_event_id is None


async def test_cluster_below_ambiguous_is_new_without_weak_model() -> None:
    async def forbidden(left: str, right: str) -> bool:
        raise AssertionError("weak model must not be called for < 0.75")

    candidate = ClusterCandidate("cluster-3", 0.74, "other event", uuid4())
    result = await resolve_cluster("new text", [candidate], forbidden)
    assert result.decision == "new_cluster"
    assert result.cluster_key != "cluster-3"

    empty = await resolve_cluster("new text", [], forbidden)
    assert empty.decision == "new_cluster"
    assert empty.similarity == 0.0


async def test_continuation_yes_and_no() -> None:
    async def yes(text: str) -> bool:
        return True

    async def no(text: str) -> bool:
        return False

    assert await continue_theme("text", yes) is True
    assert await continue_theme("text", no) is False


def test_influence_levels() -> None:
    assert influence_level([1, 2], {}) == NONE
    assert influence_level([1], {1: 0.6}) == INDIRECT
    assert influence_level([1], {1: 1.0}) == DIRECT


def test_fallback_importance_and_feed_routing() -> None:
    important = fallback_importance("ЦБ повысил ключевую ставку на 2 п.п.", [1], INDIRECT)
    weak = fallback_importance("Погода в Москве завтра", [], INDIRECT)
    assert important >= FEED_IMPORTANCE_THRESHOLD
    assert weak < FEED_IMPORTANCE_THRESHOLD
    assert route_post(INDIRECT, important) == "feed"
    assert route_post(INDIRECT, weak) == "hidden_weak"
    assert route_post(DIRECT, 99) == "feed"
    assert route_post(NONE, 99) == "ignored"


class _FakeLLM:
    def __init__(self) -> None:
        self.models: list[str | None] = []

    async def complete_json(self, **kwargs):
        self.models.append(kwargs.get("model"))
        return {"importance": 77, "impact": "risk", "rationale": "from model"}


async def test_importance_uses_weak_for_indirect_and_strong_for_direct(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from back.services import pipeline

    fake = _FakeLLM()
    monkeypatch.setattr(pipeline, "get_llm", lambda: fake)
    parsed = parse_post({"text": "ЦБ повысил ключевую ставку"})
    settings = get_settings()

    indirect = await decide_importance(parsed, [1], INDIRECT, use_llm=True)
    direct = await decide_importance(parsed, [1], DIRECT, use_llm=True)

    assert indirect.role == "weak"
    assert indirect.model == settings.weak_model
    assert dummy_first(fake.models) == settings.weak_model
    assert direct.role == DIRECT
    assert direct.model == settings.strong_model
    assert fake.models[-1] == settings.strong_model
    assert indirect.importance == direct.importance == 77


def dummy_first(items: list[str | None]) -> str | None:
    return items[0]
