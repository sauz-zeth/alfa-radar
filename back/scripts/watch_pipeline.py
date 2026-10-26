"""Print recent and newly processed posts with their ML/profile decisions."""

from __future__ import annotations

import asyncio
import json
from contextlib import suppress
from typing import Any
from uuid import UUID

from sqlalchemy import select

from back.db.models import Category, EventAnalysis, Post
from back.db.session import SessionLocal


def format_post(post: Any, categories: dict[int, str], analyses: list[dict[str, str]]) -> str:
    labels = [
        categories.get(int(category_id), str(category_id)) for category_id in post.categories or []
    ]
    return "\n".join(
        (
            f"[{post.status}/{post.stage}] post={post.id} source={post.source_name or '-'}",
            f"title: {post.title}",
            f"text: {post.text}",
            f"url: {post.url or '-'}",
            f"categories: {', '.join(labels) or '-'}",
            f"cluster: {post.cluster_key or '-'} similarity={post.similarity}",
            f"event: {post.news_event_id or '-'} importance={post.importance}",
            f"profiles: {json.dumps(analyses, ensure_ascii=False) if analyses else '-'}",
            f"error: {post.last_error or '-'}",
            "-" * 80,
        )
    )


async def watch(interval: float = 2.0) -> None:
    seen: dict[UUID, tuple[Any, ...]] = {}
    while True:
        async with SessionLocal() as session:
            posts = list(
                (
                    await session.execute(
                        select(Post).order_by(Post.created_at.desc()).limit(50)
                    )
                ).scalars()
            )
            category_names = dict((await session.execute(select(Category.id, Category.name))).all())
            event_ids = [post.news_event_id for post in posts if post.news_event_id]
            analysis_rows = []
            if event_ids:
                analysis_rows = list(
                    (
                        await session.execute(
                            select(
                                EventAnalysis.profile_id,
                                EventAnalysis.event_id,
                                EventAnalysis.status,
                            )
                            .where(EventAnalysis.event_id.in_(event_ids))
                        )
                    ).all()
                )
        analyses_by_event: dict[UUID, list[dict[str, str]]] = {}
        for profile_id, event_id, status in analysis_rows:
            analyses_by_event.setdefault(event_id, []).append(
                {"profile_id": str(profile_id), "status": status}
            )
        for post in reversed(posts):
            state = (
                post.status,
                post.stage,
                tuple(post.categories or []),
                post.cluster_key,
                post.news_event_id,
                post.importance,
                post.last_error,
                tuple(
                    sorted(
                        (item["profile_id"], item["status"])
                        for item in analyses_by_event.get(post.news_event_id, [])
                    )
                ),
            )
            if seen.get(post.id) != state:
                analyses = analyses_by_event.get(post.news_event_id, [])
                print(
                    format_post(post, category_names, analyses),
                    flush=True,
                )
                seen[post.id] = state
        await asyncio.sleep(interval)


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        asyncio.run(watch())
