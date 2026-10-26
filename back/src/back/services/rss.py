"""RSS/Atom reader that feeds posts into the news pipeline."""

import logging
import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from back.db.models import BusinessProfile, Post
from back.services.media import save_remote_post_media
from back.services.parsing import clean_text, parse_post, parse_published_at

logger = logging.getLogger(__name__)

USER_AGENT = "AlfaFutureNewsBot/1.0"
TEXT_TAGS = ("description", "summary", "content", "encoded")
DATE_TAGS = ("pubDate", "published", "updated", "date")
IMAGE_TAGS = {"thumbnail", "content", "enclosure", "image", "media"}


class _OpenGraphImage(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.url: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "meta":
            return
        values = {key.lower(): value for key, value in attrs}
        if any(values.get(key, "").lower() == "og:image" for key in ("property", "name")):
            self.url = values.get("content")


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


def _images(node: ET.Element) -> list[str]:
    result: list[str] = []
    for child in node.iter():
        name = _local(child.tag).lower()
        if name not in IMAGE_TAGS:
            continue
        if name == "enclosure" and not (child.get("type") or "").lower().startswith("image/"):
            continue
        value = child.get("url") or child.get("href") or child.get("src")
        if not value and name == "content":
            value = child.get("url")
        if value and value not in result:
            result.append(value)
    for child in node.iter():
        if _local(child.tag).lower() not in {"description", "summary", "content", "encoded"}:
            continue
        for token in child.itertext():
            if "<img" in token.lower():
                for value in re.findall(r'<img[^>]+(?:src|data-src)=["\']([^"\']+)', token, re.I):
                    if value not in result:
                        result.append(value)
    return result


def _date(value: str) -> str:
    if not value:
        return datetime.now(UTC).isoformat()
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return parse_published_at(value).isoformat()
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.isoformat()


def parse_feed(xml_text: str, feed_url: str = "") -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid or empty RSS/Atom XML: {exc}") from exc
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
                "images": _images(entry),
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
        items = parse_feed(response.text, url)
        for item in items:
            item["images"] = [urljoin(item.get("url") or url, image) for image in item["images"]]
            if item["images"] or not item.get("url"):
                continue
            try:
                page = await client.get(item["url"])
                page.raise_for_status()
                parser = _OpenGraphImage()
                parser.feed(page.text)
                if parser.url:
                    item["images"] = [urljoin(item["url"], parser.url)]
            except (httpx.HTTPError, ValueError):
                continue
        return items
    finally:
        if owns_client:
            await client.aclose()


async def ingest_feed(
    session: AsyncSession,
    url: str,
    profile: BusinessProfile | None = None,
    client: httpx.AsyncClient | None = None,
    limit: int | None = None,
    since: datetime | None = None,
    skip_existing: bool = True,
) -> tuple[int, int]:
    items = await fetch_feed(url, client)
    if since is not None:
        items = [
            item
            for item in items
            if since <= datetime.fromisoformat(item["published_at"]).astimezone(UTC)
        ]
    if limit is not None:
        items = items[:limit]
    ingested = 0
    skipped = 0
    for item in items:
        link = item.get("url")
        if skip_existing and link and await session.scalar(select(Post.id).where(Post.url == link)):
            skipped += 1
            logger.info("rss duplicate url=%s", link)
            continue
        item["media"] = []
        parsed = parse_post(item)
        post = Post(
            source_name=parsed.source_name,
            title=parsed.title,
            text=parsed.text,
            url=parsed.url,
            published_at=parsed.published_at,
            raw=item,
            parsed=parsed.as_dict(),
            status="received",
            stage="received",
            decision_trace=[{"stage": "parse", **parsed.as_dict()}],
            media=[],
        )
        post.raw = item
        session.add(post)
        await session.flush()
        if item.get("images"):
            post.media = await save_remote_post_media(
                item["images"], item.get("source") or "RSS", post.id, client
            )
            post.raw = {**item, "media": post.media}
            logger.info(
                "rss media post_id=%s downloaded=%d failed=%d",
                post.id,
                sum("error" not in image for image in post.media),
                sum("error" in image for image in post.media),
            )
        await session.commit()
        ingested += 1
        logger.info(
            "rss queued source=%s published_at=%s title=%r url=%s",
            item.get("source"),
            item.get("published_at"),
            item.get("title"),
            link,
        )
    logger.info(
        "rss ingest url=%s fetched=%s ingested=%s skipped=%s",
        url,
        len(items),
        ingested,
        skipped,
    )
    return ingested, skipped
