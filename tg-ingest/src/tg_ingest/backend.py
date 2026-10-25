import asyncio
import logging
from typing import Any

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
