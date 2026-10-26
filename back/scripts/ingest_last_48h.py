"""Import RSS news published in the last 48 hours and process them with the ML worker.

Run from back/: uv run python scripts/ingest_last_48h.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from sqlalchemy import func, select

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml_pipeline.worker import Worker, WorkerSettings

from back.config import get_settings
from back.core.sources import rss_feed_urls
from back.db.models import BusinessProfile, Post, User
from back.db.session import SessionLocal
from back.services.rss import ingest_feed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def process_pending(worker: Worker, since: datetime) -> int:
    processed = 0
    while count := await worker.run_once():
        processed += count
        await log_progress(since)
    return processed


async def log_progress(since: datetime) -> tuple[int, int]:
    async with SessionLocal() as session:
        rows = await session.execute(
            select(Post.status, func.count(Post.id))
            .where(Post.published_at >= since)
            .group_by(Post.status)
        )
        counts = dict(rows.all())
    total = sum(counts.values())
    done = counts.get("clustered", 0) + counts.get("failed", 0)
    remaining = total - done
    percent = done * 100 // total if total else 100
    logger.info(
        "ML progress: %d/%d завершено (%d%%); clustered=%d failed=%d received=%d "
        "retry=%d processing=%d",
        done,
        total,
        percent,
        counts.get("clustered", 0),
        counts.get("failed", 0),
        counts.get("received", 0),
        counts.get("retry", 0),
        counts.get("processing", 0),
    )
    if remaining:
        logger.info("ML progress: осталось или ожидает повтора=%d", remaining)
    return done, total


async def ingest_sources(
    feeds: list[str], since: datetime, client: httpx.AsyncClient
) -> int:
    settings = get_settings()
    ingested_total = 0
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.login == settings.demo_full_login))
        profile = None
        if user:
            profile = await session.scalar(
                select(BusinessProfile).where(BusinessProfile.user_id == user.id)
            )
        for index, url in enumerate(feeds, start=1):
            logger.info("Источник %d/%d: %s", index, len(feeds), url)
            try:
                ingested, skipped = await ingest_feed(
                    session, url, profile, client, since=since, skip_existing=True
                )
                ingested_total += ingested
                logger.info(
                    "Источник %d/%d завершён: новых=%d уже загруженных пропущено=%d",
                    index,
                    len(feeds),
                    ingested,
                    skipped,
                )
            except (httpx.HTTPError, ValueError) as exc:
                logger.error("Источник %d/%d ошибка: %s", index, len(feeds), exc)
    return ingested_total


async def main() -> None:
    feeds = rss_feed_urls()
    logger.info("Использую первые %d прямых RSS-источников каталога", len(feeds))

    since = datetime.now(UTC) - timedelta(hours=48)
    logger.info(
        "Начинаю импорт новостей с %s; RSS-лент: %s",
        since.isoformat(),
        len(feeds),
    )
    worker_settings = replace(WorkerSettings.from_app(), enabled=True)
    worker = Worker(SessionLocal, worker_settings)
    resumed = await process_pending(worker, since)
    logger.info("Возобновлена обработка уже загруженных новостей: %d", resumed)
    await log_progress(since)

    async with httpx.AsyncClient(
        timeout=20, follow_redirects=True, headers={"User-Agent": "AlfaFutureNewsBot/1.0"}
    ) as client:
        total_ingested = await ingest_sources(feeds, since, client)

    logger.info("Импорт завершён: новых новостей=%d", total_ingested)
    processed = await process_pending(worker, since)
    logger.info("ML-очередь доступных записей закончилась; обработано=%d", processed)
    await log_progress(since)


if __name__ == "__main__":
    asyncio.run(main())
