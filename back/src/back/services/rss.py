"""RSS/Atom reader that feeds posts into the news pipeline."""

import logging
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from back.db.models import BusinessProfile, Post
from back.services.parsing import clean_text, parse_published_at
from back.services.pipeline import ingest_post

logger = logging.getLogger(__name__)

USER_AGENT = "AlfaFutureNewsBot/1.0"
TEXT_TAGS = ("description", "summary", "content", "encoded")
DATE_TAGS = ("pubDate", "published", "updated", "date")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text(node: ET.Element) -> str:
    return clean_text(" ".join(node.itertext()))


def _child_text(node: ET.Element, names: tuple[str, ...]) -> str:
    for child in node:
        if _local(child.tag) in names:
            value = _text(child)
            if value:
                return value
    return ""


def _link(node: ET.Element) -> str | None:
    fallback: str | None = None
    for child in node:
        if _local(child.tag) != "link":
            continue
        href = clean_text(child.get("href"))
        if href:
            if child.get("rel", "alternate") == "alternate":
                return href
            fallback = fallback or href
        value = _text(child)
        if value:
            return value
    return fallback


def _date(value: str) -> str:
    if not value:
        return datetime.now(UTC).isoformat()
    try:
        parsed = parsedate_to_datetime(value)
    except TypeError, ValueError:
        return parse_published_at(value).isoformat()
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.isoformat()


def parse_feed(xml_text: str, feed_url: str = "") -> list[dict[str, Any]]:
    root = ET.fromstring(xml_text)
    container = next(
        (child for child in root if _local(child.tag) in {"channel", "feed"}),
        root,
    )
    feed_title = _child_text(container, ("title",))
    source = feed_title or httpx.URL(feed_url).host or "RSS"
    result: list[dict[str, Any]] = []
    for entry in root.iter():
        if _local(entry.tag) not in {"item", "entry"}:
            continue
        title = _child_text(entry, ("title",))
        text = _child_text(entry, TEXT_TAGS)
        if not title and not text:
            continue
        result.append(
            {
                "title": title,
                "text": text or title,
                "source": _child_text(entry, ("source", "author")) or source,
                "url": _link(entry),
                "published_at": _date(_child_text(entry, DATE_TAGS)),
            }
        )
    return result


async def fetch_feed(url: str, client: httpx.AsyncClient | None = None) -> list[dict[str, Any]]:
    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(
            timeout=20, follow_redirects=True, headers={"User-Agent": USER_AGENT}
        )
    try:
        response = await client.get(url)
        response.raise_for_status()
    finally:
        if owns_client:
            await client.aclose()
    return parse_feed(response.text, url)


async def ingest_feed(
    session: AsyncSession,
    url: str,
    profile: BusinessProfile | None = None,
    client: httpx.AsyncClient | None = None,
    limit: int | None = None,
) -> tuple[int, int]:
    items = await fetch_feed(url, client)
    if limit is not None:
        items = items[:limit]
    ingested = 0
    skipped = 0
    for item in items:
        link = item.get("url")
        if link and await session.scalar(select(Post.id).where(Post.url == link)):
            skipped += 1
            continue
        await ingest_post(session, item, profile)
        ingested += 1
    logger.info("rss %s: ingested=%s skipped=%s", url, ingested, skipped)
    return ingested, skipped
