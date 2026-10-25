import asyncio
import json
import logging
import random
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError, UserAlreadyParticipantError
from telethon.tl.functions.channels import GetFullChannelRequest, JoinChannelRequest
from telethon.tl.types import Channel

from .backend import update_channel_stats, upload_avatar
from .config import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChannelInfo:
    id: str
    handle: str
    avatar_url: str | None = None
    subscribers: int = 1
    manual_subscribers: int = 0
    tg_subscribers: int | None = None


def _key(handle: str) -> str:
    return handle.strip().lstrip("@").lower()


def _keyed(infos: list[ChannelInfo]) -> dict[str, ChannelInfo]:
    return {_key(info.handle): info for info in infos}


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


async def fetch_channels(http: httpx.AsyncClient, settings: Settings) -> list[ChannelInfo]:
    response = await http.get(
        settings.channels_path, headers={"X-Ingest-Token": settings.ingest_token}
    )
    response.raise_for_status()
    items = response.json().get("items", [])
    return [
        ChannelInfo(
            id=str(item["id"]),
            handle=str(item["handle"]),
            avatar_url=item.get("avatar_url"),
            subscribers=int(item.get("subscribers", 0)),
            manual_subscribers=int(item.get("manual_subscribers", 0)),
            tg_subscribers=item.get("tg_subscribers"),
        )
        for item in items
        if item.get("handle")
    ]


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
        self._avatar_checked: set[str] = set()
        self._stats_checked: set[str] = set()
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

    async def _cache_stats(
        self, http: httpx.AsyncClient, entity: Any, info: ChannelInfo
    ) -> None:
        if info.id in self._stats_checked:
            return
        count = getattr(entity, "participants_count", None)
        if count is None and info.tg_subscribers is None:
            try:
                full = await self.client(GetFullChannelRequest(entity))
                count = getattr(full.full_chat, "participants_count", None)
            except Exception as exc:
                logger.warning("cannot read subscriber count %s: %s", info.handle, exc)
        self._stats_checked.add(info.id)
        if count is None or count == info.tg_subscribers:
            return
        try:
            await update_channel_stats(http, self.settings, info.id, int(count))
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            logger.warning("cannot cache subscriber count %s: %s", info.handle, exc)

    async def _cache_avatar(
        self, http: httpx.AsyncClient, entity: Any, info: ChannelInfo
    ) -> None:
        key = _key(info.handle)
        if key in self._avatar_checked:
            return
        try:
            photo = await self.client.download_profile_photo(entity, file=bytes)
        except Exception as exc:
            logger.warning("cannot download avatar %s: %s", info.handle, exc)
            return
        if not photo:
            self._avatar_checked.add(key)
            return
        try:
            await upload_avatar(http, self.settings, info.id, photo)
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            logger.warning("cannot upload avatar %s: %s", info.handle, exc)
            return
        self._avatar_checked.add(key)

    async def sync(self, http: httpx.AsyncClient, *, join: bool = True) -> None:
        self._joins_cycle = 0
        manual = _keyed(
            [
                ChannelInfo(id="", handle=handle, manual_subscribers=1)
                for handle in self.settings.channels
            ]
        )
        try:
            fetched = await fetch_channels(http, self.settings)
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            logger.warning("cannot fetch channels from backend: %s", exc)
            wanted = manual
        else:
            wanted = {**manual, **_keyed(fetched)}
        infos = list(wanted.values())
        join_targets = [info for info in infos if info.subscribers > 0 or not info.id]
        join_targets.sort(
            key=lambda info: (
                -info.manual_subscribers,
                -info.subscribers,
                info.handle.lower(),
            )
        )
        for info in join_targets:
            key = _key(info.handle)
            if self._cooling(key):
                continue
            entity = await self._resolve(info.handle)
            if entity is None:
                continue
            if entity.id in self._joined_ids:
                self._joined.add(key)
            if join:
                await self._join(info.handle, entity)
            if key in self._joined:
                self._active_ids.add(entity.id)
            if join and info.id:
                await self._cache_stats(http, entity, info)
            if join and info.id and not info.avatar_url:
                await self._cache_avatar(http, entity, info)

        if join:
            avatar_targets = [
                info
                for info in infos
                if info.id and info.subscribers <= 0 and not info.avatar_url
            ]
            for info in avatar_targets[: self.settings.avatar_batch]:
                key = _key(info.handle)
                if key in self._avatar_checked or self._cooling(key):
                    continue
                entity = await self._resolve(info.handle)
                if entity is None:
                    continue
                await self._cache_avatar(http, entity, info)

        self._active_ids = {self._entities[key].id for key in wanted if key in self._joined}
