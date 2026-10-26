"""Recalculate ML screening importance for existing news from the last 48 hours."""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml_pipeline.repository import PostRepository
from ml_pipeline.worker import WorkerSettings, _profile_analysis

from back.db.models import BusinessProfile, NewsEvent
from back.db.session import SessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    since = datetime.now(UTC) - timedelta(hours=48)
    settings = WorkerSettings.from_app()
    async with SessionLocal() as session:
        events = list(
            (
                await session.execute(
                    select(NewsEvent)
                    .where(NewsEvent.published_at >= since, NewsEvent.is_active.is_(True))
                    .order_by(NewsEvent.published_at, NewsEvent.id)
                )
            ).scalars()
        )
        profiles = list(
            (await session.execute(select(BusinessProfile).order_by(BusinessProfile.id))).scalars()
        )
        event_rows = [
            (event.id, list(event.source_posts or []), list(event.category_ids or []))
            for event in events
        ]
        profile_rows = [
            (profile.id, profile.business_name, profile.role, profile.reporting_summary or {})
            for profile in profiles
        ]
        repo = PostRepository(session)
        logger.info(
            "Пересчёт ML importance: новостей=%d профилей=%d окно_с=%s",
            len(events),
            len(profiles),
            since.isoformat(),
        )
        total = len(event_rows) * len(profile_rows)
        done = 0
        for event_index, (event_id, sources, category_ids) in enumerate(event_rows, start=1):
            logger.info("Новость %d/%d: %s", event_index, len(event_rows), event_id)
            event = NewsEvent(
                id=event_id,
                source_posts=sources,
                category_ids=category_ids,
                published_at=since,
            )
            for profile_index, (profile_id, business_name, role, reporting) in enumerate(
                profile_rows, start=1
            ):
                done += 1
                try:
                    source_count = await repo.event_source_count(event_id, profile_id)
                    categories = await repo.profile_categories(profile_id)
                    profile = BusinessProfile(
                        id=profile_id,
                        business_name=business_name,
                        role=role,
                        reporting_summary=reporting,
                    )
                    await _profile_analysis(
                        repo, event, profile, categories, source_count, settings
                    )
                    await session.commit()
                except Exception:
                    await session.rollback()
                    logger.exception(
                        "Ошибка пересчёта %d/%d event_id=%s profile_id=%s",
                        done,
                        total,
                        event_id,
                        profile_id,
                    )
                    continue
                logger.info(
                    "Прогресс %d/%d: event_id=%s profile=%d/%d business=%r",
                    done,
                    total,
                    event_id,
                    profile_index,
                    len(profiles),
                    business_name,
                )
    logger.info("Пересчёт завершён: обработано комбинаций новость-профиль=%d", done)


if __name__ == "__main__":
    asyncio.run(main())
