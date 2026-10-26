"""News-processing pipeline.

Global stages: parse -> classify -> cluster -> continuation.
Per-profile stages: influence -> importance -> feed/tracked routing.

Thresholds live here only. ML (ruBERT/e5) and model decisions are pluggable stubs;
the branching logic itself is real.
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from back.config import get_settings
from back.db.models import BusinessCategory, BusinessProfile, NewsEvent, Post, TrackedItem
from back.llm.factory import get_llm
from back.llm.prompts import (
    CONTINUATION_SYSTEM,
    IMPORTANCE_SYSTEM,
    SAME_EVENT_SYSTEM,
    continuation_prompt,
    importance_prompt,
    same_event_prompt,
)
from back.services.agent import analyze_event
from back.services.feed import match_event
from back.services.ml import centroid, cosine, get_classifier, normalize
from back.services.parsing import ParsedPost, parse_post
from back.services.personalization import load_categories, load_counterparties

logger = logging.getLogger(__name__)

SAME_CLUSTER_THRESHOLD = 0.85
AMBIGUOUS_CLUSTER_THRESHOLD = 0.75
FEED_IMPORTANCE_THRESHOLD = 30
DIRECT_INFLUENCE_WEIGHT = 0.8
CANDIDATE_LIMIT = 300

SOURCE_CLUSTER = "source_cluster"
NEW_CLUSTER = "new_cluster"
NONE = "none"
INDIRECT = "indirect"
DIRECT = "direct"

_CONTINUATION_MARKERS = (
    "продолж",
    "второй этап",
    "новый этап",
    "уточн",
    "дополн",
    "ранее сообщал",
    "обновлен",
    "обновлён",
)
_IMPACT_RISK = ("повыс", "сниз", "запрет", "огранич", "штраф", "рост цен", "потеря")
_IMPACT_OPPORTUNITY = ("льгот", "субсиди", "снижен", "поддерж", "выгод", "рост спроса")


@dataclass(frozen=True)
class ClusterCandidate:
    cluster_key: str
    similarity: float
    sample_text: str
    news_event_id: UUID | None


@dataclass(frozen=True)
class ClusterResult:
    similarity: float
    decision: str
    cluster_key: str
    news_event_id: UUID | None


@dataclass(frozen=True)
class ImportanceDecision:
    importance: int
    impact: str
    rationale: str
    role: str
    model: str


async def classify(parsed: ParsedPost) -> tuple[list[int], list[float]]:
    classification = await get_classifier().classify(parsed.title, parsed.text)
    return classification.categories, classification.embedding


def _token_overlap(left: str, right: str) -> float:
    left_tokens = {token for token in normalize(left).split() if len(token) >= 4}
    right_tokens = {token for token in normalize(right).split() if len(token) >= 4}
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))


async def decide_same_event(text: str, cluster_sample: str) -> bool:
    fallback = {"same_event": _token_overlap(text, cluster_sample) >= 0.5}
    if not get_settings().llm_ml_enabled:
        return bool(fallback["same_event"])
    result = await get_llm().complete_json(
        system=SAME_EVENT_SYSTEM,
        user=same_event_prompt(text, cluster_sample),
        fallback=fallback,
        model=get_settings().weak_model,
    )
    return bool(result.get("same_event"))


async def resolve_cluster(
    text: str,
    candidates: list[ClusterCandidate],
    decider: Callable[[str, str], Awaitable[bool]] | None = None,
) -> ClusterResult:
    best = max(candidates, key=lambda item: item.similarity) if candidates else None
    similarity = best.similarity if best is not None else 0.0
    if best is not None and similarity >= SAME_CLUSTER_THRESHOLD:
        return ClusterResult(similarity, SOURCE_CLUSTER, best.cluster_key, best.news_event_id)
    same_event = False
    if best is not None and similarity >= AMBIGUOUS_CLUSTER_THRESHOLD:
        same_event = await (decider or decide_same_event)(text, best.sample_text)
    if same_event and best is not None:
        return ClusterResult(similarity, SOURCE_CLUSTER, best.cluster_key, best.news_event_id)
    return ClusterResult(similarity, NEW_CLUSTER, uuid4().hex[:16], None)


async def load_candidates(
    session: AsyncSession, embedding: list[float]
) -> list[ClusterCandidate]:
    rows = list(
        (
            await session.execute(
                select(Post)
                .where(Post.cluster_key.is_not(None), Post.embedding.is_not(None))
                .order_by(Post.created_at.desc())
                .limit(CANDIDATE_LIMIT)
            )
        ).scalars()
    )
    # shortcut: centroid is computed on the fly from recent posts; move to a cluster table at scale.
    groups: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not row.cluster_key or not row.embedding:
            continue
        group = groups.setdefault(
            row.cluster_key,
            {"vectors": [], "sample_text": row.text, "news_event_id": row.news_event_id},
        )
        group["vectors"].append(row.embedding)
        if group["news_event_id"] is None and row.news_event_id is not None:
            group["news_event_id"] = row.news_event_id
    result: list[ClusterCandidate] = []
    for cluster_key, group in groups.items():
        vector = centroid(list(group["vectors"]))
        result.append(
            ClusterCandidate(
                cluster_key=cluster_key,
                similarity=cosine(embedding, vector),
                sample_text=str(group["sample_text"]),
                news_event_id=group["news_event_id"],
            )
        )
    result.sort(key=lambda item: item.similarity, reverse=True)
    return result


async def decide_continuation(text: str) -> bool:
    lowered = normalize(text)
    fallback = {"continue_theme": any(marker in lowered for marker in _CONTINUATION_MARKERS)}
    if not get_settings().llm_ml_enabled:
        return bool(fallback["continue_theme"])
    result = await get_llm().complete_json(
        system=CONTINUATION_SYSTEM,
        user=continuation_prompt(text),
        fallback=fallback,
        model=get_settings().weak_model,
    )
    return bool(result.get("continue_theme"))


async def continue_theme(
    text: str, decider: Callable[[str], Awaitable[bool]] | None = None
) -> bool:
    return await (decider or decide_continuation)(text)


def influence_level(category_ids: list[int], profile_weights: dict[int, float]) -> str:
    matched = [
        weight
        for category_id, weight in profile_weights.items()
        if category_id in category_ids and weight > 0
    ]
    if not matched:
        return NONE
    return DIRECT if max(matched) >= DIRECT_INFLUENCE_WEIGHT else INDIRECT


def guess_impact(text: str) -> str:
    lowered = normalize(text)
    risk = any(marker in lowered for marker in _IMPACT_RISK)
    opportunity = any(marker in lowered for marker in _IMPACT_OPPORTUNITY)
    if risk and opportunity:
        return "mixed"
    if risk:
        return "risk"
    if opportunity:
        return "opportunity"
    return "neutral"


def fallback_importance(text: str, categories: list[int], level: str) -> int:
    lowered = normalize(text)
    score = 20 + min(len(categories), 3) * 4
    boosters = ("ставк", "пошлин", "санкц", "налог", "цб", "тариф", "огранич", "повыс")
    if any(marker in lowered for marker in boosters):
        score += 20
    if len(lowered) > 300:
        score += 5
    if level == DIRECT:
        score += 5
    return max(1, min(100, score))


async def decide_importance(
    parsed: ParsedPost,
    categories: list[int],
    level: str,
    profile_context: dict[str, Any] | None = None,
    use_llm: bool | None = None,
) -> ImportanceDecision:
    settings = get_settings()
    fallback_score = fallback_importance(parsed.text, categories, level)
    fallback: dict[str, Any] = {
        "importance": fallback_score,
        "impact": guess_impact(parsed.text),
        "rationale": (
            "Детерминированная оценка по категориям и ключевым словам "
            f"(уровень влияния: {level})."
        ),
    }
    role = DIRECT if level == DIRECT else "weak"
    model = settings.strong_model if role == DIRECT else settings.weak_model
    enabled = settings.llm_ml_enabled if use_llm is None else use_llm
    if not enabled:
        return ImportanceDecision(
            int(fallback["importance"]),
            str(fallback["impact"]),
            str(fallback["rationale"]),
            role,
            model,
        )
    result = await get_llm().complete_json(
        system=IMPORTANCE_SYSTEM,
        user=importance_prompt(parsed.text, categories, level, profile_context or {}),
        fallback=fallback,
        model=model,
    )
    try:
        importance = max(1, min(100, int(result.get("importance", fallback_score))))
    except (TypeError, ValueError):
        importance = fallback_score
    impact = str(result.get("impact") or fallback["impact"])
    if impact not in {"risk", "opportunity", "mixed", "neutral"}:
        impact = str(fallback["impact"])
    return ImportanceDecision(
        importance,
        impact,
        str(result.get("rationale") or fallback["rationale"]),
        role,
        model,
    )


def route_post(level: str, importance: int) -> str:
    if level == NONE:
        return "ignored"
    if importance < FEED_IMPORTANCE_THRESHOLD:
        return "hidden_weak"
    return "feed"


def _source_payload(parsed: ParsedPost, *, primary: bool = True) -> dict[str, Any]:
    return {
        "name": parsed.source_name,
        "time": parsed.published_at.isoformat(),
        "tone": "neutral",
        "text": parsed.text,
        "url": parsed.url,
        "is_primary": primary,
    }


def _profile_payload(profile: BusinessProfile) -> dict[str, Any]:
    return {
        "profile_id": str(profile.id),
        "business_name": profile.business_name,
        "role": profile.role,
    }


async def _profile_weights(session: AsyncSession, profile: BusinessProfile) -> dict[int, float]:
    rows = (
        await session.execute(
            select(BusinessCategory.category_id, BusinessCategory.weight).where(
                BusinessCategory.profile_id == profile.id
            )
        )
    ).all()
    return {int(category_id): float(weight) for category_id, weight in rows}


def _create_event(
    parsed: ParsedPost,
    categories: list[int],
    importance: int,
    impact: str,
    rationale: str,
    *,
    chain_key: str | None = None,
    feed_visible: bool = True,
) -> NewsEvent:
    summary = parsed.text[:600]
    return NewsEvent(
        title=parsed.title,
        summary=summary,
        what_it_means=rationale,
        source_name=parsed.source_name,
        source_url=parsed.url,
        published_at=parsed.published_at,
        importance=importance,
        impact=impact,
        category_ids=categories,
        mentioned_company_uids=[],
        facts=[{"text": summary, "status": "Источник"}],
        source_posts=[_source_payload(parsed)],
        impact_metrics=[],
        chain_key=chain_key,
        is_active=True,
        is_feed_visible=feed_visible,
    )


async def _attach_to_event(
    session: AsyncSession, post: Post, event_id: UUID, parsed: ParsedPost
) -> NewsEvent | None:
    event = await session.get(NewsEvent, event_id)
    if event is None:
        return None
    payload = _source_payload(parsed, primary=False)
    existing = event.source_posts or []
    if not any(item.get("text") == payload["text"] for item in existing if isinstance(item, dict)):
        event.source_posts = [*existing, payload]
    post.news_event_id = event.id
    return event


async def _create_tracked(
    session: AsyncSession,
    profile: BusinessProfile,
    parsed: ParsedPost,
    categories: list[int],
    importance: int,
    impact: str,
    rationale: str,
    chain_key: str | None = None,
) -> tuple[NewsEvent, TrackedItem]:
    event = _create_event(
        parsed,
        categories,
        importance,
        impact,
        rationale,
        chain_key=chain_key,
        feed_visible=False,
    )
    session.add(event)
    await session.flush()

    business_categories = await load_categories(session, profile)
    counterparties = await load_counterparties(session, profile)
    match = match_event(event, business_categories, counterparties)
    report = await analyze_event(
        profile=profile,
        event=event,
        business_categories=business_categories,
        counterparties=counterparties,
        match_importance=match.importance,
        matched_counterparties=match.matched_counterparties,
        use_llm=get_settings().llm_agent_enabled,
        events=[event],
    )
    tracked = TrackedItem(
        profile_id=profile.id,
        event_id=event.id,
        status="active",
        title=event.title,
        event_ids=[str(event.id)],
        report=report,
    )
    session.add(tracked)
    await session.flush()
    return event, tracked


async def ingest_post(
    session: AsyncSession, payload: dict[str, Any], profile: BusinessProfile | None = None
) -> Post:
    parsed = parse_post(payload)
    trace: list[dict[str, Any]] = [{"stage": "parse", **parsed.as_dict()}]
    post = Post(
        source_name=parsed.source_name,
        title=parsed.title,
        text=parsed.text,
        url=parsed.url,
        published_at=parsed.published_at,
        raw=payload,
        parsed=parsed.as_dict(),
        status="received",
        stage="received",
        decision_trace=trace,
    )
    session.add(post)
    await session.flush()

    categories, embedding = await classify(parsed)
    post.categories = categories
    post.embedding = embedding
    post.stage = "classify"
    trace.append(
        {
            "stage": "classify",
            "categories": categories,
            "embedding_dim": len(embedding),
            "provider": "stub",
        }
    )

    candidates = await load_candidates(session, embedding)
    cluster = await resolve_cluster(parsed.text, candidates)
    post.cluster_key = cluster.cluster_key
    post.similarity = round(cluster.similarity, 4)
    post.stage = "cluster"
    trace.append(
        {
            "stage": "cluster",
            "similarity": round(cluster.similarity, 4),
            "decision": cluster.decision,
            "cluster_key": cluster.cluster_key,
            "candidates": len(candidates),
            "thresholds": {
                "same": SAME_CLUSTER_THRESHOLD,
                "ambiguous": AMBIGUOUS_CLUSTER_THRESHOLD,
            },
        }
    )
    if cluster.decision == SOURCE_CLUSTER:
        post.status = SOURCE_CLUSTER
        if cluster.news_event_id is not None:
            await _attach_to_event(session, post, cluster.news_event_id, parsed)
            trace.append(
                {
                    "stage": "routing",
                    "status": SOURCE_CLUSTER,
                    "news_event_id": str(cluster.news_event_id),
                    "note": "источник кластера, LLM не вызывался",
                }
            )
        else:
            trace.append(
                {
                    "stage": "routing",
                    "status": SOURCE_CLUSTER,
                    "note": "источник кластера без привязанного события",
                }
            )
        post.decision_trace = trace
        flag_modified(post, "decision_trace")
        await session.commit()
        await session.refresh(post)
        return post

    post.stage = "continuation"
    continued = await continue_theme(parsed.text)
    trace.append({"stage": "continuation", "continue_theme": continued})
    if continued:
        post.status = "tracked"
        if profile is None:
            trace.append(
                {
                    "stage": "routing",
                    "status": "tracked",
                    "note": "профиль не передан: отслеживание не создано",
                }
            )
        else:
            importance = fallback_importance(parsed.text, categories, DIRECT)
            event, tracked = await _create_tracked(
                session,
                profile,
                parsed,
                categories,
                importance,
                guess_impact(parsed.text),
                "Продолжение темы: событие отслеживается, в ленту не попадает.",
                post.cluster_key,
            )
            post.news_event_id = event.id
            post.tracked_item_id = tracked.id
            post.importance = importance
            trace.append(
                {
                    "stage": "routing",
                    "status": "tracked",
                    "news_event_id": str(event.id),
                    "tracked_item_id": str(tracked.id),
                    "profile_id": str(profile.id),
                    "note": "в ленту не попадает",
                }
            )
        post.decision_trace = trace
        flag_modified(post, "decision_trace")
        await session.commit()
        await session.refresh(post)
        return post

    post.stage = "influence"
    if profile is None:
        post.status = "clustered"
        trace.append(
            {
                "stage": "routing",
                "status": "clustered",
                "note": "профиль не передан: влияние и лента пропущены",
            }
        )
        post.decision_trace = trace
        flag_modified(post, "decision_trace")
        await session.commit()
        await session.refresh(post)
        return post

    weights = await _profile_weights(session, profile)
    level = influence_level(categories, weights)
    trace.append(
        {
            "stage": "influence",
            "level": level,
            "profile_id": str(profile.id),
            "matched_categories": sorted(set(weights) & set(categories)),
        }
    )
    if level == NONE:
        post.status = "ignored"
        trace.append({"stage": "routing", "status": "ignored", "note": "нет влияния на профиль"})
        post.decision_trace = trace
        flag_modified(post, "decision_trace")
        await session.commit()
        await session.refresh(post)
        return post

    decision = await decide_importance(
        parsed, categories, level, {"profile": _profile_payload(profile), "weights": weights}
    )
    post.importance = decision.importance
    trace.append(
        {
            "stage": "importance",
            "importance": decision.importance,
            "impact": decision.impact,
            "rationale": decision.rationale,
            "role": decision.role,
            "model": decision.model,
        }
    )

    event = _create_event(
        parsed,
        categories,
        decision.importance,
        decision.impact,
        decision.rationale,
        chain_key=post.cluster_key,
    )
    session.add(event)
    await session.flush()
    post.news_event_id = event.id
    post.status = route_post(level, decision.importance)
    trace.append(
        {
            "stage": "routing",
            "status": post.status,
            "news_event_id": str(event.id),
            "feed_threshold": FEED_IMPORTANCE_THRESHOLD,
        }
    )
    post.decision_trace = trace
    flag_modified(post, "decision_trace")
    await session.commit()
    await session.refresh(post)
    return post


async def ingest_from_profile(
    session: AsyncSession, payload: dict[str, Any], profile_id: UUID | None
) -> Post:
    profile: BusinessProfile | None = None
    if profile_id is not None:
        profile = (
            await session.execute(
                select(BusinessProfile)
                .options(selectinload(BusinessProfile.company))
                .where(BusinessProfile.id == profile_id)
            )
        ).scalar_one_or_none()
        if profile is None:
            raise LookupError("profile not found")
    return await ingest_post(session, payload, profile)
