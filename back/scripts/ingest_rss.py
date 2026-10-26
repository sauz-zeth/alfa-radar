"""Read RSS/Atom feeds and push their items through the ingestion pipeline.

Usage (from back/):
    uv run python scripts/ingest_rss.py
    uv run python scripts/ingest_rss.py https://example.com/rss https://example.com/atom

Feeds without arguments come from RSS_FEEDS (comma-separated).
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select

from back.config import get_settings
from back.db.models import BusinessProfile, User
from back.db.session import SessionLocal
from back.services.rss import ingest_feed


async def main(urls: list[str]) -> None:
    settings = get_settings()
    if not urls:
        urls = settings.rss_feed_list
    if not urls:
        print("rss: no feeds configured (pass URLs or set RSS_FEEDS)")
        return

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

        async with httpx.AsyncClient(
            timeout=20, follow_redirects=True, headers={"User-Agent": "AlfaFutureNewsBot/1.0"}
        ) as client:
            for url in urls:
                try:
                    ingested, skipped = await ingest_feed(
                        session, url, profile, client, since=datetime.now(UTC) - timedelta(hours=48)
                    )
                except (httpx.HTTPError, ValueError) as exc:
                    print(f"{url}: failed ({exc})")
                    continue
                print(f"{url}: ingested={ingested} skipped={skipped}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
