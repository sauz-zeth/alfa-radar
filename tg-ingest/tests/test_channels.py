from pathlib import Path
from typing import Any

from tg_ingest import channels as channels_module
from tg_ingest.channels import ChannelInfo, ChannelRegistry
from tg_ingest.config import Settings


class FakeEntity:
    def __init__(self, entity_id: int) -> None:
        self.id = entity_id


class FakeClient:
    def __init__(self, entities: dict[str, int]) -> None:
        self.entities = entities
        self.joins: list[Any] = []

    async def get_entity(self, handle: str) -> FakeEntity:
        return FakeEntity(self.entities[handle.lstrip("@").lower()])

    async def __call__(self, request: Any) -> None:
        self.joins.append(request)


def _settings(tmp_path: Path, **overrides: Any) -> Settings:
    values = {
        "api_id": 1,
        "api_hash": "hash",
        "channels": (),
        "join_retry_seconds": 600,
        "join_delay_min": 0,
        "join_delay_max": 0,
        "join_batch": 10,
        "join_daily_limit": 100,
        "join_state": tmp_path / "joins.json",
    }
    values.update(overrides)
    return Settings(**values)


async def test_sync_joins_backend_channels_and_prunes(monkeypatch, tmp_path) -> None:
    wanted = {"@from_backend": 10, "@manual": 20}

    async def fake_fetch(http, settings) -> list[ChannelInfo]:
        handles = list(wanted) if settings.channels == () else ["@from_backend"]
        return [ChannelInfo(id="", handle=handle) for handle in handles]

    monkeypatch.setattr(channels_module, "fetch_channels", fake_fetch)
    client = FakeClient({"from_backend": 10, "manual": 20})
    settings = _settings(tmp_path, channels=("@manual",))
    registry = ChannelRegistry(client, settings)  # type: ignore[arg-type]

    await registry.sync(None)  # type: ignore[arg-type]
    assert registry.active_ids == {10, 20}
    assert len(client.joins) == 2

    async def fake_empty(http, settings) -> list[ChannelInfo]:
        return []

    monkeypatch.setattr(channels_module, "fetch_channels", fake_empty)
    await registry.sync(None)  # type: ignore[arg-type]
    assert registry.active_ids == {20}


async def test_sync_survives_broken_channel(monkeypatch, tmp_path) -> None:
    async def fake_fetch(http, settings) -> list[ChannelInfo]:
        return [ChannelInfo(id="", handle=handle) for handle in ("@broken", "@ok")]

    monkeypatch.setattr(channels_module, "fetch_channels", fake_fetch)
    client = FakeClient({"ok": 30})
    registry = ChannelRegistry(client, _settings(tmp_path))  # type: ignore[arg-type]

    await registry.sync(None)  # type: ignore[arg-type]

    assert registry.active_ids == {30}


async def test_daily_join_limit_is_persisted(monkeypatch, tmp_path) -> None:
    async def fake_fetch(http, settings) -> list[ChannelInfo]:
        return [ChannelInfo(id="", handle=handle) for handle in ("@a", "@b")]

    monkeypatch.setattr(channels_module, "fetch_channels", fake_fetch)
    client = FakeClient({"a": 1, "b": 2})
    settings = _settings(tmp_path, join_daily_limit=1, join_batch=10)
    registry = ChannelRegistry(client, settings)  # type: ignore[arg-type]

    await registry.sync(None)  # type: ignore[arg-type]
    await registry.sync(None)  # type: ignore[arg-type]

    assert len(client.joins) == 1
    assert len(registry.active_ids) == 1
    assert (tmp_path / "joins.json").exists()


async def test_avatar_is_uploaded_once(monkeypatch, tmp_path) -> None:
    class AvatarClient(FakeClient):
        async def download_profile_photo(self, entity, file=None) -> bytes:
            return b"\xff\xd8\xfffake-jpeg"

    uploaded: list[tuple[str, bytes]] = []

    async def fake_upload(http, settings, channel_id, photo):
        uploaded.append((channel_id, photo))
        return "/static/avatars/ch-1.jpg"

    async def fake_fetch(http, settings) -> list[ChannelInfo]:
        return [ChannelInfo(id="ch-1", handle="@avatared", avatar_url=None)]

    monkeypatch.setattr(channels_module, "fetch_channels", fake_fetch)
    monkeypatch.setattr(channels_module, "upload_avatar", fake_upload)
    client = AvatarClient({"avatared": 40})
    registry = ChannelRegistry(client, _settings(tmp_path))  # type: ignore[arg-type]

    await registry.sync(None)  # type: ignore[arg-type]
    await registry.sync(None)  # type: ignore[arg-type]

    assert uploaded == [("ch-1", b"\xff\xd8\xfffake-jpeg")]
