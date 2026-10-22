from typing import Any

from back.core.sources import (
    CHANNELS,
    RECOMMENDED_IDS,
    ChannelSeed,
    find_channel,
    parse_handle,
    search_channels,
)
from back.db.models import BusinessProfile
from back.schemas.sources import ChannelCatalogResponse, ChannelOut, SourcesState


def _default_sources() -> dict[str, Any]:
    return {
        "channels": list(RECOMMENDED_IDS),
        "custom": [],
    }


def ensure_sources(profile: BusinessProfile) -> dict[str, Any]:
    if not profile.sources:
        profile.sources = _default_sources()
        return profile.sources
    sources = dict(profile.sources)
    sources.setdefault("channels", list(RECOMMENDED_IDS))
    sources.setdefault("custom", [])
    profile.sources = sources
    return sources


def _custom_channels(profile: BusinessProfile) -> list[dict[str, Any]]:
    custom = ensure_sources(profile).get("custom") or []
    return [item for item in custom if isinstance(item, dict) and item.get("id")]


def _channel_out(item: ChannelSeed, subscribed: set[str], *, kind: str = "catalog") -> ChannelOut:
    return ChannelOut(
        id=item.id,
        name=item.name,
        handle=item.handle,
        topics=item.topics,
        kind=kind,
        subscribed=item.id in subscribed,
        recommended=item.id in RECOMMENDED_IDS,
    )


def sources_state(profile: BusinessProfile) -> SourcesState:
    sources = ensure_sources(profile)
    subscribed = {str(item) for item in sources.get("channels", [])}
    custom = _custom_channels(profile)
    custom_ids = {str(item["id"]) for item in custom}
    channels = [_channel_out(item, subscribed) for item in CHANNELS if item.id in subscribed]
    for item in custom:
        if str(item["id"]) in subscribed:
            channels.append(
                ChannelOut(
                    id=str(item["id"]),
                    name=str(item.get("name") or item["id"]),
                    handle=item.get("handle"),
                    topics=str(item.get("topics") or "добавлен вами"),
                    kind="custom",
                    subscribed=True,
                )
            )
    return SourcesState(
        channels=channels,
        recommended_count=len(RECOMMENDED_IDS),
        custom_count=len(custom_ids),
        catalog_total=len(CHANNELS),
    )


def catalog(profile: BusinessProfile, query: str) -> ChannelCatalogResponse:
    sources = ensure_sources(profile)
    subscribed = {str(item) for item in sources.get("channels", [])}
    items = [_channel_out(item, subscribed) for item in search_channels(query)]
    for item in _custom_channels(profile):
        custom_id = str(item["id"])
        haystack = f"{custom_id} {item.get('name', '')} {item.get('handle', '')}".lower()
        if query.strip().lower() in haystack or not query.strip():
            items.insert(
                0,
                ChannelOut(
                    id=custom_id,
                    name=str(item.get("name") or custom_id),
                    handle=item.get("handle"),
                    topics=str(item.get("topics") or "добавлен вами"),
                    kind="custom",
                    subscribed=custom_id in subscribed,
                ),
            )
    return ChannelCatalogResponse(query=query, items=items, total=len(items))


def subscribe(profile: BusinessProfile, query: str) -> SourcesState:
    sources = ensure_sources(profile)
    seed = find_channel(query)
    handle = parse_handle(query)
    if seed is not None:
        channel_id = seed.id
    elif handle:
        channel_id = handle.lower().lstrip("@")
        custom = _custom_channels(profile)
        if not any(str(item["id"]) == channel_id for item in custom):
            custom.append(
                {
                    "id": channel_id,
                    "name": handle,
                    "handle": handle,
                    "topics": "добавлен вами",
                }
            )
        sources["custom"] = custom
    else:
        raise LookupError("Не удалось распознать канал. Укажите @тег или ссылку t.me.")
    channels = [str(item) for item in sources.get("channels", [])]
    if channel_id not in channels:
        channels.insert(0, channel_id)
    sources["channels"] = channels
    profile.sources = sources
    return sources_state(profile)


def unsubscribe(profile: BusinessProfile, channel_id: str) -> SourcesState:
    sources = ensure_sources(profile)
    sources["channels"] = [
        str(item) for item in sources.get("channels", []) if str(item) != channel_id
    ]
    profile.sources = sources
    return sources_state(profile)


def unsubscribe_all(profile: BusinessProfile) -> SourcesState:
    sources = ensure_sources(profile)
    sources["channels"] = []
    profile.sources = sources
    return sources_state(profile)


def restore_recommended(profile: BusinessProfile) -> SourcesState:
    sources = ensure_sources(profile)
    sources["channels"] = list(RECOMMENDED_IDS)
    profile.sources = sources
    return sources_state(profile)
