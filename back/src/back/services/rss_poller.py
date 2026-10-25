import asyncio
import logging

import httpx
from sqlalchemy import select

from back.config import get_settings
from back.db.models import Channel, ProfileChannel
from back.db.session import SessionLocal
from back.services.rss import ingest_feed

logger = logging.getLogger(__name__)


async def subscribed_feed_urls() -> list[str]:
    async with SessionLocal() as session:
        rows = await session.execute(
            select(Channel.meta["feed_url"].astext)
            .join(ProfileChannel, ProfileChannel.channel_id == Channel.id)
            .where(
                Channel.is_active.is_(True),
                Channel.meta["feed_url"].astext.is_not(None),
            )
            .distinct()
        )
        return [str(row[0]) for row in rows]


async def _poll_feed(
    url: str,
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    limit: int,
) -> None:
    async with semaphore, SessionLocal() as session:
        try:
            await ingest_feed(session, url, client=client, limit=limit)
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("rss %s: failed (%s)", url, exc)
            await session.rollback()
        except Exception:
            logger.exception("rss %s: unexpected failure", url)
            await session.rollback()


async def poll_once() -> None:
    settings = get_settings()
    urls = await subscribed_feed_urls()
    if not urls:
        return
    semaphore = asyncio.Semaphore(settings.rss_poll_concurrency)
    async with httpx.AsyncClient(
        timeout=20, follow_redirects=True, headers={"User-Agent": "AlfaFutureNewsBot/1.0"}
    ) as client:
        await asyncio.gather(
            *(
                _poll_feed(url, client, semaphore, settings.rss_poll_items_limit)
                for url in urls
            )
        )


async def rss_poll_loop() -> None:
    settings = get_settings()
    await asyncio.sleep(settings.rss_poll_initial_delay_seconds)
    while True:
        try:
            await poll_once()
        except Exception:
            logger.exception("rss poller iteration failed")
        await asyncio.sleep(settings.rss_poll_interval_seconds)
