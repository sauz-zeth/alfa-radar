import asyncio
import logging
from typing import Any
from urllib.parse import quote

import httpx

from .config import Settings

logger = logging.getLogger(__name__)

PERMANENT_STATUSES = {401, 403, 404, 422}


async def send_post(http: httpx.AsyncClient, settings: Settings, payload: dict[str, Any]) -> bool:
    headers = {"X-Ingest-Token": settings.ingest_token}
    for attempt in range(1, settings.retries + 1):
        try:
            response = await http.post(settings.ingest_path, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            logger.warning("backend unavailable (%s/%s): %s", attempt, settings.retries, exc)
        else:
            if response.status_code < 400:
                logger.info(
                    "ingested %s from %s", response.json().get("id"), payload["source_name"]
                )
                return True
            logger.warning(
                "backend rejected post (%s): %s %s",
                response.status_code,
                attempt,
                response.text[:300],
            )
            if response.status_code in PERMANENT_STATUSES:
                return False
        if attempt < settings.retries:
            await asyncio.sleep(2 ** (attempt - 1))
    logger.error("post dropped after %s attempts: %s", settings.retries, payload["url"])
    return False


async def update_channel_stats(
    http: httpx.AsyncClient,
    settings: Settings,
    channel_id: str,
    subscribers: int,
    title: str | None = None,
) -> None:
    payload: dict[str, Any] = {"subscribers": subscribers}
    if title:
        payload["title"] = title
    response = await http.put(
        f"/api/ingest/channels/{quote(channel_id, safe='')}/stats",
        json=payload,
        headers={"X-Ingest-Token": settings.ingest_token},
    )
    response.raise_for_status()
    logger.info("cached %s subscribers for %s (title=%r)", subscribers, channel_id, title)


async def upload_avatar(
    http: httpx.AsyncClient, settings: Settings, channel_id: str, photo: bytes
) -> str:
    response = await http.put(
        f"/api/ingest/channels/{quote(channel_id, safe='')}/avatar",
        content=photo,
        headers={"X-Ingest-Token": settings.ingest_token, "Content-Type": "image/jpeg"},
    )
    response.raise_for_status()
    avatar_url = str(response.json()["avatar_url"])
    logger.info("cached avatar for %s: %s", channel_id, avatar_url)
    return avatar_url
