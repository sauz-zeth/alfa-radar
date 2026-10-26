"""Lease, classify, cluster, and personalize newly ingested posts."""

from __future__ import annotations

import asyncio
import logging
import signal
from contextlib import suppress
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import UUID

from back.config import get_settings
from back.db.models import NewsEvent, Post
from back.llm.factory import get_llm
from back.services.parsing import clean_text
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .adapter import classify_post
from .contracts import NormalizedPost
from .repository import PostRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class WorkerSettings:
    batch_size: int = 20
    lease_seconds: int = 300
    max_attempts: int = 5
    poll_interval_seconds: float = 10
    enabled: bool = False
    kimi_model: str = "moonshotai/kimi-k2.6"
    screening_model: str = "model service"

    @classmethod
    def from_app(cls) -> WorkerSettings:
        settings = get_settings()
        return cls(
            settings.ml_worker_batch_size,
            settings.ml_worker_lease_seconds,
            settings.ml_worker_max_attempts,
            settings.ml_worker_poll_interval_seconds,
            settings.ml_worker_enabled,
            settings.ml_kimi_model,
            settings.ml_screening_model,
        )


class _Classifier:
    """Adapter from the existing ruBERT classifier to the runtime contract."""

    def __init__(self) -> None:
        from pathlib import Path

        from ml_artifact.core.news_cluster_reranker import LocalReranker, OnnxEmbedder
        from ml_artifact.core.onnx_rubert_classifier import RubertOnnxClassifier

        root = Path(get_settings().ml_artifact_root)
        if not root.is_absolute() and not root.exists():
            root = Path(__file__).resolve().parents[1] / root
        root = root / "models"
        model_paths = (
            root / "rubert_int4" / "metadata.json",
            root / "rubert_int4" / "model.onnx",
            root / "rubert_int4" / "tokenizer",
            root / "bge_m3_int8" / "model_quantized.onnx",
            root / "bge_m3_int8" / "tokenizer.json",
            root / "bge_reranker_int8" / "model_quantized.onnx",
            root / "bge_reranker_int8" / "tokenizer.json",
        )
        missing = [str(path) for path in model_paths if not path.exists()]
        if missing:
            raise FileNotFoundError("ML model files are missing: " + ", ".join(missing))
        try:
            self.rubert = RubertOnnxClassifier(root / "rubert_int4")
            self.embedder = OnnxEmbedder(root / "bge_m3_int8")
            self.reranker = LocalReranker(root / "bge_reranker_int8")
        except ImportError as exc:
            raise RuntimeError(
                f"ML dependency is missing ({exc.name}); install dependencies with `uv sync`"
            ) from exc

    def predict(self, texts: list[str]) -> list[dict[str, Any]]:
        return self.rubert.predict(texts)

    def embed(self, text: str) -> list[float]:
        return self.embedder.encode([text[:1200]])[0].tolist()


def _labels(post: Post) -> list[dict[str, Any]]:
    value = post.categories or []
    if value and isinstance(value[0], int):
        from back.core.categories import CATEGORY_BY_ID

        return [
            {"id": item, "label": CATEGORY_BY_ID[item].name, "score": 1.0}
            for item in value
            if item in CATEGORY_BY_ID
        ]
    return [dict(item) for item in value if isinstance(item, dict)]


async def _cluster(
    repo: PostRepository,
    post: Post,
    normalized: NormalizedPost,
    decision: Any,
    reranker: Any,
    category_ids_by_name: dict[str, int],
) -> tuple[NewsEvent, str]:
    import numpy as np
    from ml_artifact.core.image_utils import image_source_is_excluded
    from ml_artifact.core.news_cluster_reranker import (
        DEFAULT_COSINE_THRESHOLD,
        DEFAULT_RERANKER_THRESHOLD,
        representative_text,
    )

    since = post.published_at - timedelta(hours=24)
    # Serialize candidate selection for the same publication day, then lock the chosen event key.
    await repo.lock_cluster(f"feed-day:{post.published_at.date().isoformat()}")
    event_rows = await repo.candidate_events(since)
    events = [event for event, _last_seen in event_rows]
    last_seen_by_id = {event.id: last_seen for event, last_seen in event_rows}
    members = await repo.event_member_posts([event.id for event in events], since)
    event_by_id = {event.id: event for event in events}
    grouped: dict[UUID, list[Post]] = {}
    for member in members:
        grouped.setdefault(member.news_event_id, []).append(member)
    vector = np.asarray(decision.embedding, dtype=np.float32)
    candidates = []
    for event_id, items in grouped.items():
        if post.published_at - last_seen_by_id[event_id] > timedelta(hours=24):
            continue
        if any(item.source_name == post.source_name for item in items):
            continue
        vectors = np.asarray([item.embedding for item in items], dtype=np.float32)
        center = vectors.mean(axis=0)
        norm = np.linalg.norm(center)
        similarity = float(vector @ (center / norm)) if norm > 1e-12 else 0.0
        if similarity >= DEFAULT_COSINE_THRESHOLD:
            cluster = type("Cluster", (), {})()
            cluster.members = [
                {"text": item.text, "date": item.published_at.isoformat()} for item in items[-3:]
            ]
            cluster.sources = {item.source_name for item in items}
            cluster.sum_vector = vectors.sum(axis=0)
            cluster.last_seen_at = last_seen_by_id[event_id]
            cluster.event_id = str(event_id)
            candidates.append((similarity, event_by_id[event_id], cluster))
    candidates.sort(key=lambda item: (-item[0], str(item[1].id)))
    candidates = candidates[:8]
    selected = None
    if candidates:
        logits = np.asarray(
            reranker.rank(
                decision.text[:2000], [representative_text(item[2]) for item in candidates[:8]], 16
            )
        )
        if logits.shape != (len(candidates),) or not np.isfinite(logits).all():
            raise ValueError("Reranker returned invalid logits")
        best = int(np.argmax(logits))
        if logits[best] >= DEFAULT_RERANKER_THRESHOLD:
            candidate_event = candidates[best][1]
            await repo.lock_cluster(candidate_event.chain_key or str(candidate_event.id))
            selected = candidate_event
    label_ids = {
        category_ids_by_name[label]: float(item.get("score", 0))
        for item in decision.labels
        if (label := str(item.get("label", ""))) in category_ids_by_name
    }
    source = {
        "post_id": str(post.id),
        "source": normalized.source,
        "date": post.published_at.isoformat(),
        "text": decision.text,
        "url": normalized.url,
        "media": list(normalized.media),
        "image_url": next(
            (str(image["origin_url"]) for image in normalized.media if image.get("origin_url")),
            None,
        ),
        "labels": list(decision.labels),
    }
    if selected is None:
        await repo.lock_cluster(f"post:{post.id}")
        initial_media = [
            dict(image)
            for image in normalized.media
            if not image.get("error")
            and not image_source_is_excluded(image.get("source") or normalized.source)
        ]
        event = NewsEvent(
            title=normalized.title or decision.text[:120],
            summary=decision.text[:600],
            what_it_means="",
            source_name=normalized.source,
            source_url=normalized.url,
            published_at=post.published_at,
            category_ids=sorted(label_ids),
            source_posts=[source],
            media=initial_media[:4],
            chain_key=f"feed:{post.id.hex}",
        )
        repo.session.add(event)
        await repo.session.flush()
    else:
        event = selected
        sources = list(event.source_posts or [])
        if not any(str(item.get("post_id")) == str(post.id) for item in sources):
            sources.append(source)
        event.source_posts = sources
        event.category_ids = sorted(set(event.category_ids or []) | set(label_ids))
        media = list(event.media or [])
        seen = {
            str(item.get(key))
            for item in media
            for key in ("image_id", "sha256", "perceptual_hash")
            if item.get(key)
        }
        for image in normalized.media:
            if len(media) >= 4:
                break
            if image.get("error") or image_source_is_excluded(
                image.get("source") or normalized.source
            ):
                continue
            image_keys = {
                str(image.get(key))
                for key in ("image_id", "sha256", "perceptual_hash")
                if image.get(key)
            }
            if image_keys.isdisjoint(seen):
                media.append(dict(image))
                seen.update(image_keys)
        event.media = media
    return event, str(event.chain_key or event.id)


async def _profile_analysis(
    repo: PostRepository,
    event: NewsEvent,
    profile: Any,
    categories: dict[str, float],
    source_count: int,
    settings: WorkerSettings,
) -> None:
    from .llm_routes import route_profile_analysis

    labels = {
        str(item.get("label", ""))
        for source in event.source_posts
        for item in source.get("labels", [])
    }
    matched = {name: weight for name, weight in categories.items() if name in labels}
    if not matched:
        logger.info(
            "ml profile event_id=%s profile_id=%s status=ignored matched_categories=[] feed=no",
            event.id,
            profile.id,
        )
        await repo.upsert_profile_score(
            profile.id,
            event.id,
            {
                "status": "ignored",
                "importance": 0,
                "related": False,
                "direct": False,
                "fact": False,
                "within_month": False,
                "independent_source_count": source_count,
            },
        )
        await repo.upsert_analysis(
            profile.id,
            event.id,
            {
                "status": "ignored",
                "related": False,
                "direct": False,
                "fact": False,
                "within_month": False,
                "independent_source_count": source_count,
                "why": [],
            },
        )
        return
    level = "direct" if max(matched.values()) >= 0.8 else "indirect"
    cluster = {
        "sources": event.source_posts,
        "category_ids": list(event.category_ids),
        "influence": level,
    }
    result = await route_profile_analysis(
        cluster,
        {
            "business_name": profile.business_name,
            "role": profile.role,
            "categories": matched,
            "reporting_summary": profile.reporting_summary or {},
        },
        get_llm(),
        kimi_model=settings.kimi_model,
        screening_model=settings.screening_model,
    )
    await repo.upsert_profile_score(
        profile.id,
        event.id,
        {
            "status": result.status,
            "importance": result.importance,
            "related": result.related,
            "direct": result.direct,
            "fact": result.fact,
            "within_month": result.within_month,
            "why": list(result.why),
            "independent_source_count": source_count,
            "why": list(result.why),
        },
    )
    await repo.upsert_analysis(
        profile.id,
        event.id,
        {
            "status": result.status,
            "impact": result.impact,
            "related": result.related,
            "direct": result.direct,
            "fact": result.fact,
            "within_month": result.within_month,
            "independent_source_count": source_count,
        },
    )
    logger.info(
        "ml profile event_id=%s profile_id=%s user_id=%s business=%r status=%s related=%s "
        "direct=%s importance=%s matched_categories=%s feed=%s",
        event.id,
        profile.id,
        profile.user_id,
        profile.business_name,
        result.status,
        result.related,
        result.direct,
        result.importance,
        sorted(matched),
        result.status != "ignored",
    )


async def process_post(
    session: AsyncSession, post: Post, classifier: Any, reranker: Any, settings: WorkerSettings
) -> None:
    repo = PostRepository(session)
    try:
        source = post.source_name or ""
        clean = clean_text(f"{post.title} {post.text}")
        normalized = NormalizedPost(
            str(post.id),
            source,
            clean,
            post.title,
            post.url,
            post.published_at,
            media=tuple(post.media or []),
            raw=post.raw or {},
        )
        decision = classify_post(normalized, classifier)
        logger.info(
            "ml classify post_id=%s source=%s status=%s labels=%s",
            post.id,
            source,
            decision.status,
            [item.get("label") for item in decision.labels],
        )
        if decision.status != "accepted":
            post.status, post.stage = "failed", decision.status
            post.last_error = decision.status
            post.lease_until = None
            await session.commit()
            logger.info("ml rejected post_id=%s status=%s", post.id, decision.status)
            return
        category_ids = await repo.category_ids()
        if post.news_event_id:
            event = await session.get(NewsEvent, post.news_event_id)
            if event is None:
                raise LookupError(f"linked event {post.news_event_id} no longer exists")
            key = post.cluster_key or str(event.chain_key or event.id)
        else:
            if reranker is None:
                from ml_artifact.core.news_cluster_reranker import LocalReranker

                reranker = LocalReranker()
            event, key = await _cluster(repo, post, normalized, decision, reranker, category_ids)
        logger.info(
            "ml cluster post_id=%s event_id=%s cluster_key=%s source_count=%s",
            post.id,
            event.id,
            key,
            len(event.source_posts or []),
        )
        stored_labels = [
            category_ids[label]
            for label in (str(item.get("label", "")) for item in decision.labels)
            if label in category_ids
        ]
        await repo.mark_clustered(post, event, key, stored_labels, list(decision.embedding))
        profiles = await repo.profiles()
        logger.info(
            "ml profile routing post_id=%s event_id=%s profiles=%d",
            post.id,
            event.id,
            len(profiles),
        )
        for profile in profiles:
            count = await repo.event_source_count(event.id, profile.id)
            await _profile_analysis(
                repo, event, profile, await repo.profile_categories(profile.id), count, settings
            )
        await session.commit()
    except Exception as error:
        post_id = post.id
        attempts = int(post.attempt_count or 0) + 1
        await session.rollback()
        message = f"{type(error).__name__}: {error}"
        if attempts >= settings.max_attempts:
            await repo.mark_failed(post_id, message)
            logger.exception("ml failed post_id=%s attempt=%d: %s", post_id, attempts, message)
        else:
            await repo.mark_retry(post_id, message, min(3600, 2**attempts * 30))
            logger.exception("ml retry post_id=%s attempt=%d: %s", post_id, attempts, message)
        await session.commit()


class Worker:
    def __init__(
        self, sessions: async_sessionmaker[AsyncSession], settings: WorkerSettings | None = None
    ) -> None:
        self.sessions = sessions
        self.settings = settings or WorkerSettings.from_app()
        self.stop_event = asyncio.Event()
        self._classifier: Any = None
        self._reranker: Any = None

    def stop(self) -> None:
        self.stop_event.set()

    async def run_once(self) -> int:
        if self._classifier is None:
            self._classifier = _Classifier()
            self._reranker = self._classifier.reranker
        async with self.sessions() as session:
            repo = PostRepository(session)
            posts = await repo.claim_batch(self.settings.batch_size, self.settings.lease_seconds)
            await session.commit()
        if posts:
            logger.info("ml claimed batch size=%d", len(posts))
        for index, post in enumerate(posts, start=1):
            if self.stop_event.is_set():
                break
            async with self.sessions() as session:
                post = await session.get(Post, post.id)
                if post:
                    await process_post(
                        session, post, self._classifier, self._reranker, self.settings
                    )
                    status = await session.scalar(select(Post.status).where(Post.id == post.id))
                    logger.info(
                        "ml progress batch=%d/%d post_id=%s status=%s",
                        index,
                        len(posts),
                        post.id,
                        status or "missing",
                    )
        return len(posts)

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            with suppress(NotImplementedError, RuntimeError):
                loop.add_signal_handler(sig, self.stop)
        while not self.stop_event.is_set():
            if self.settings.enabled:
                count = await self.run_once()
            else:
                count = 0
            if not count:
                with suppress(TimeoutError):
                    await asyncio.wait_for(
                        self.stop_event.wait(), self.settings.poll_interval_seconds
                    )


async def _main() -> None:
    from back.db.session import SessionLocal

    await Worker(SessionLocal).run()


if __name__ == "__main__":
    asyncio.run(_main())
