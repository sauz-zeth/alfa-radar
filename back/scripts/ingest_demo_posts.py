"""Ingest demo posts through the real pipeline.

Usage (from back/):
    uv run python scripts/ingest_demo_posts.py
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select

from back.config import get_settings
from back.db.models import BusinessProfile, User
from back.db.session import SessionLocal
from back.services.pipeline import ingest_post

SAMPLES = [
    {
        "title": "ЦБ повысил ключевую ставку до 21%",
        "text": (
            "Банк России повысил ключевую ставку на 2 п.п. до 21%. "
            "Решение повышает стоимость кредитов для бизнеса."
        ),
        "source": "ЦБ РФ",
        "url": "https://example.local/news/rate-21",
        "published_at": datetime.now(UTC).isoformat(),
    },
    {
        "text": (
            "Банк России повысил ключевую ставку на 2 п.п. до 21%. "
            "Решение повышает стоимость кредитов для бизнеса."
        ),
        "source": "Деловой вестник",
        "url": "https://example.local/news/rate-21-daily",
    },
    {
        "title": "Уточнение по экспортной пошлине на металлопрокат",
        "text": (
            "Ранее сообщали о 7% пошлины. Минфин уточнил: ставка вступит в силу "
            "с 1 ноября и не имеет исключений для подписанных контрактов."
        ),
        "source": "Минфин",
    },
    {
        "title": "Погода в Москве",
        "text": "Синоптики обещают тёплые выходные без осадков.",
        "source": "Погода",
    },
]


async def main() -> None:
    settings = get_settings()
    async with SessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.login == settings.demo_full_login))
        ).scalar_one_or_none()
        profile = None
        if user is not None:
            profile = (
                await session.execute(
                    select(BusinessProfile).where(BusinessProfile.user_id == user.id)
                )
            ).scalar_one_or_none()
        for sample in SAMPLES:
            post = await ingest_post(session, sample, profile)
            print(
                f"{post.id} status={post.status} stage={post.stage} "
                f"cluster={post.cluster_key} similarity={post.similarity} "
                f"event={post.news_event_id} tracked={post.tracked_item_id}"
            )


if __name__ == "__main__":
    asyncio.run(main())
