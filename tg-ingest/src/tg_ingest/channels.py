import asyncio
import json
import logging
import random
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError, UserAlreadyParticipantError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import Channel

from .config import Settings

logger = logging.getLogger(__name__)


def _key(handle: str) -> str:
    return handle.strip().lstrip("@").lower()


def _keyed(handles: list[str]) -> dict[str, str]:
    return {_key(handle): handle for handle in handles}


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


async def fetch_channels(http: httpx.AsyncClient, settings: Settings) -> list[str]:
    response = await http.get(
        settings.channels_path, headers={"X-Ingest-Token": settings.ingest_token}
    )
    response.raise_for_status()
    items = response.json().get("items", [])
    return [str(item["handle"]) for item in items if item.get("handle")]


class JoinLimiter:
    """Persistent daily cap plus human-like pauses between joins."""

    def __init__(self, path: Path, limit: int) -> None:
        self.path = path
        self.limit = limit
        self._date = _today()
        self._count = self._load()
        self._warned = False

    def _load(self) -> int:
        try:
            data = json.loads(self.path.read_text())
            if data.get("date") == _today():
                return int(data.get("count", 0))
        except (OSError, ValueError, TypeError):
            pass
        return 0

    def _rollover(self) -> None:
        today = _today()
        if today != self._date:
            self._date = today
            self._count = 0
            self._warned = False

    def can_join(self) -> bool:
        self._rollover()
        if self.limit <= 0:
            return True
        if self._count >= self.limit:
            if not self._warned:
                logger.warning(
                    "daily join limit %s reached, waiting until tomorrow", self.limit
                )
                self._warned = True
            return False
        return True

    def record(self) -> None:
        self._rollover()
        self._count += 1
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_name(self.path.name + ".tmp")
            tmp.write_text(json.dumps({"date": self._date, "count": self._count}))
            tmp.replace(self.path)
        except OSError as exc:
            logger.warning("cannot persist join counter: %s", exc)


class ChannelRegistry:
    """Joins the twin account to channels people subscribe to in the backend."""

    def __init__(self, client: TelegramClient, settings: Settings) -> None:
        self.client = client
        self.settings = settings
        self._entities: dict[str, Any] = {}
        self._joined: set[str] = set()
        self._joined_ids: set[int] = set()
        self._failed: dict[str, float] = {}
        self._active_ids: set[int] = set()
        self._joins_cycle = 0
        self.limiter = JoinLimiter(settings.join_state, settings.join_daily_limit)

    @property
    def active_ids(self) -> set[int]:
        return self._active_ids

    async def load_dialogs(self) -> None:
        try:
            async for dialog in self.client.iter_dialogs():
                if isinstance(dialog.entity, Channel):
                    self._joined_ids.add(dialog.entity.id)
        except Exception as exc:
            logger.warning("cannot load dialogs: %s", exc)

    def _cooling(self, key: str) -> bool:
        return (
            time.monotonic() - self._failed.get(key, float("-inf"))
            < self.settings.join_retry_seconds
        )

    async def _resolve(self, handle: str) -> Any | None:
        key = _key(handle)
        entity = self._entities.get(key)
        if entity is not None:
            return entity
        try:
            entity = await self.client.get_entity(handle)
        except Exception as exc:
            self._failed[key] = time.monotonic()
            logger.warning("cannot resolve %s: %s", handle, exc)
            return None
        self._entities[key] = entity
        return entity

    async def _join(self, handle: str, entity: Any) -> None:
        key = _key(handle)
        if key in self._joined or self._cooling(key):
            return
        if entity.id in self._joined_ids:
            self._joined.add(key)
            self._active_ids.add(entity.id)
            return
        if self._joins_cycle >= self.settings.join_batch or not self.limiter.can_join():
            return
        self._joins_cycle += 1
        delay = random.uniform(self.settings.join_delay_min, self.settings.join_delay_max)
        if delay > 0:
            logger.info("joining %s in %.0fs", handle, delay)
            await asyncio.sleep(delay)
        try:
            await self.client(JoinChannelRequest(entity))
            logger.info("joined %s", handle)
        except UserAlreadyParticipantError:
            logger.info("already subscribed to %s", handle)
        except FloodWaitError as exc:
            self._failed[key] = time.monotonic()
            logger.warning("flood wait %ss while joining %s", exc.seconds, handle)
            return
        except RPCError as exc:
            self._failed[key] = time.monotonic()
            logger.warning("cannot join %s: %s", handle, exc)
            return
        self.limiter.record()
        self._joined.add(key)
        self._joined_ids.add(entity.id)
        self._failed.pop(key, None)
        self._active_ids.add(entity.id)

    async def sync(self, http: httpx.AsyncClient, *, join: bool = True) -> None:
        self._joins_cycle = 0
        manual = _keyed(list(self.settings.channels))
        try:
            handles = await fetch_channels(http, self.settings)
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            logger.warning("cannot fetch channels from backend: %s", exc)
            wanted = manual
        else:
            wanted = {**manual, **_keyed(handles)}
        for handle in wanted.values():
            key = _key(handle)
            if self._cooling(key):
                continue
            entity = await self._resolve(handle)
            if entity is None:
                continue
            if join:
                await self._join(handle, entity)
            if key in self._joined:
                self._active_ids.add(entity.id)
        self._active_ids = {self._entities[key].id for key in wanted if key in self._joined}
