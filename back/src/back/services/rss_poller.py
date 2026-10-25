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


async def poll_once() -> None:
    urls = await subscribed_feed_urls()
    if not urls:
        return
    async with (
        httpx.AsyncClient(
            timeout=20, follow_redirects=True, headers={"User-Agent": "AlfaFutureNewsBot/1.0"}
        ) as client,
        SessionLocal() as session,
    ):
        for url in urls:
            try:
                ingested, skipped = await ingest_feed(session, url, client=client)
            except (httpx.HTTPError, ValueError) as exc:
                logger.warning("rss %s: failed (%s)", url, exc)
                await session.rollback()
                continue
            except Exception:
                logger.exception("rss %s: unexpected failure", url)
                await session.rollback()
                continue
            logger.info("rss %s: ingested=%s skipped=%s", url, ingested, skipped)


async def rss_poll_loop() -> None:
    settings = get_settings()
    await asyncio.sleep(settings.rss_poll_initial_delay_seconds)
    while True:
        try:
            await poll_once()
        except Exception:
            logger.exception("rss poller iteration failed")
        await asyncio.sleep(settings.rss_poll_interval_seconds)
