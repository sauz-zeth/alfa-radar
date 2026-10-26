from urllib.parse import urlparse

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from back.core.recommendations import candidates_by_id, recommend_ids
from back.core.sources import (
    CHANNELS,
    RECOMMENDED_IDS,
    parse_feed_url,
    parse_handle,
    rss_channel_id,
)
from back.db.models import BusinessCategory, BusinessProfile, Channel, ProfileChannel
from back.schemas.sources import ChannelCatalogResponse, ChannelOut, SourcesState
from back.services.avatars import get_avatar_url


def _channel_out(channel: Channel, subscribed: bool, recommended: bool) -> ChannelOut:
    meta = channel.meta or {}
    candidate = candidates_by_id().get(channel.id)
    return ChannelOut(
        id=channel.id,
        name=channel.name,
        handle=channel.handle,
        topics=channel.topics,
        kind=channel.kind,
        subscribed=subscribed,
        recommended=recommended,
        avatar_url=meta.get("avatar_url") or get_avatar_url(channel.id),
        feed_url=meta.get("feed_url"),
        source_type="rss" if meta.get("feed_url") else "telegram",
        tg_subscribers=meta.get("tg_subscribers"),
        popularity=candidate.popularity if candidate else meta.get("tg_subscribers"),
        category_ids=sorted(candidate.category_ids) if candidate else [],
    )


def _seed_meta(seed) -> dict:
    meta = {}
    if seed.feed_url:
        meta["feed_url"] = seed.feed_url
    if seed.subscribers is not None:
        meta["tg_subscribers"] = seed.subscribers
    if seed.popularity is not None:
        meta["rss_popularity"] = seed.popularity
    return meta


async def ensure_catalog(session: AsyncSession) -> None:
    existing = {
        row.id: row
        for row in (
            await session.execute(
                select(Channel).where(Channel.id.in_([item.id for item in CHANNELS]))
            )
        ).scalars()
    }
    for seed in CHANNELS:
        row = existing.get(seed.id)
        if row is None:
            session.add(
                Channel(
                    id=seed.id,
                    name=seed.name,
                    handle=seed.handle,
                    topics=seed.topics,
                    kind="catalog",
                    is_recommended=seed.id in RECOMMENDED_IDS,
                    meta=_seed_meta(seed),
                )
            )
        else:
            row.name = seed.name
            row.handle = seed.handle
            row.topics = seed.topics
            row.kind = "catalog"
            row.is_recommended = seed.id in RECOMMENDED_IDS
            row.meta = {**(row.meta or {}), **_seed_meta(seed)}
    await session.flush()


async def _subscription_ids(session: AsyncSession, profile: BusinessProfile) -> set[str]:
    return set(
        (
            await session.execute(
                select(ProfileChannel.channel_id).where(ProfileChannel.profile_id == profile.id)
            )
        ).scalars()
    )


async def _add_subscription(
    session: AsyncSession,
    profile: BusinessProfile,
    channel_id: str,
    source: str,
) -> None:
    exists = (
        await session.execute(
            select(ProfileChannel.id).where(
                ProfileChannel.profile_id == profile.id,
                ProfileChannel.channel_id == channel_id,
            )
        )
    ).scalar_one_or_none()
    if exists is None:
        session.add(ProfileChannel(profile_id=profile.id, channel_id=channel_id, source=source))


async def _ensure_legacy_channels(session: AsyncSession, profile: BusinessProfile) -> bool:
    legacy = profile.sources or {}
    channel_ids = [str(item) for item in legacy.get("channels") or [] if item]
    custom = [item for item in legacy.get("custom") or [] if isinstance(item, dict)]
    if not channel_ids and not custom:
        return False
    await ensure_catalog(session)
    existing = {
        row.id
        for row in (
            await session.execute(
                select(Channel).where(
                    Channel.id.in_(
                        [*channel_ids, *[str(item.get("id")) for item in custom if item.get("id")]]
                    )
                )
            )
        ).scalars()
    }
    for channel_id in channel_ids:
        if channel_id not in existing:
            session.add(
                Channel(
                    id=channel_id,
                    name=channel_id,
                    topics="перенесено из профиля",
                    kind="catalog",
                )
            )
            existing.add(channel_id)
        await _add_subscription(session, profile, channel_id, "catalog")
    for item in custom:
        channel_id = str(item.get("id") or "")
        if not channel_id:
            continue
        if channel_id not in existing:
            session.add(
                Channel(
                    id=channel_id,
                    name=str(item.get("name") or channel_id),
                    handle=item.get("handle"),
                    topics=str(item.get("topics") or "добавлен вами"),
                    kind="custom",
                )
            )
            existing.add(channel_id)
        if channel_id in channel_ids:
            await _add_subscription(session, profile, channel_id, "custom")
    return True


async def _profile_category_ids(session: AsyncSession, profile: BusinessProfile) -> set[int]:
    return set(
        (
            await session.execute(
                select(BusinessCategory.category_id).where(
                    BusinessCategory.profile_id == profile.id
                )
            )
        ).scalars()
    )


async def _recommended_ids(session: AsyncSession, profile: BusinessProfile) -> set[str]:
    return set(recommend_ids(await _profile_category_ids(session, profile)))


async def ensure_profile_sources(session: AsyncSession, profile: BusinessProfile) -> None:
    if profile.sources_initialized:
        return
    migrated = await _ensure_legacy_channels(session, profile)
    if not migrated:
        await ensure_catalog(session)
        for channel_id in await _recommended_ids(session, profile):
            await _add_subscription(session, profile, channel_id, "recommended")
    profile.sources_initialized = True
    await session.flush()


async def sources_state(session: AsyncSession, profile: BusinessProfile) -> SourcesState:
    await ensure_profile_sources(session, profile)
    subscribed = await _subscription_ids(session, profile)
    rows = list(
        (
            await session.execute(
                select(Channel)
                .where(Channel.id.in_(subscribed))
                .order_by(Channel.is_recommended.desc(), Channel.name)
            )
        ).scalars()
    )
    recommended_ids = await _recommended_ids(session, profile)
    channels = [
        _channel_out(row, True, row.id in recommended_ids) for row in rows
    ]
    channels.sort(
        key=lambda item: (not item.recommended, -(item.popularity or 0), item.name)
    )
    custom_count = sum(1 for row in rows if row.kind == "custom")
    catalog_total = (
        await session.execute(
            select(func.count())
            .select_from(Channel)
            .where(Channel.is_active.is_(True))
        )
    ).scalar_one()
    return SourcesState(
        channels=channels,
        recommended_count=len(recommended_ids),
        custom_count=custom_count,
        catalog_total=catalog_total,
    )


async def catalog(
    session: AsyncSession, profile: BusinessProfile, query: str
) -> ChannelCatalogResponse:
    await ensure_profile_sources(session, profile)
    await ensure_catalog(session)
    subscribed = await _subscription_ids(session, profile)
    text = (query or "").strip()
    statement = select(Channel).where(Channel.is_active.is_(True))
    if text:
        pattern = f"%{text}%"
        filters = [
            Channel.id.ilike(pattern),
            Channel.name.ilike(pattern),
            Channel.topics.ilike(pattern),
            Channel.handle.ilike(pattern),
            Channel.meta["feed_url"].astext.ilike(pattern),
        ]
        handle = parse_handle(text)
        if handle:
            filters.append(Channel.handle.ilike(handle))
        statement = statement.where(or_(*filters))
    rows = list(
        (await session.execute(statement.order_by(Channel.name).limit(500))).scalars()
    )
    recommended_ids = await _recommended_ids(session, profile)
    items = [
        _channel_out(row, row.id in subscribed, row.id in recommended_ids) for row in rows
    ]
    items.sort(key=lambda item: (not item.recommended, -(item.popularity or 0), item.name))
    return ChannelCatalogResponse(
        query=text,
        items=items,
        total=len(items),
    )


async def _find_channel(session: AsyncSession, query: str) -> Channel | None:
    text = (query or "").strip()
    if not text:
        return None
    feed_url = parse_feed_url(text)
    handle = parse_handle(text)
    statement = select(Channel).where(
        or_(
            Channel.id == (rss_channel_id(feed_url) if feed_url else text.lower()),
            Channel.name.ilike(f"%{text}%"),
            Channel.handle.ilike(handle or text),
            Channel.meta["feed_url"].astext == feed_url if feed_url else False,
        )
    )
    return (await session.execute(statement.limit(1))).scalar_one_or_none()


async def _custom_rss_channel(session: AsyncSession, feed_url: str) -> Channel:
    channel_id = rss_channel_id(feed_url)
    row = await session.get(Channel, channel_id)
    if row is not None:
        return row
    host = urlparse(feed_url).netloc or feed_url
    row = Channel(
        id=channel_id,
        name=host,
        topics="добавлен вами",
        kind="custom",
        meta={"feed_url": feed_url},
    )
    session.add(row)
    await session.flush()
    return row


async def _custom_channel(session: AsyncSession, handle: str) -> Channel:
    channel_id = "tg_" + handle.lstrip("@").lower()
    row = await session.get(Channel, channel_id)
    if row is None:
        row = Channel(
            id=channel_id,
            name=handle,
            handle=handle,
            topics="добавлен вами",
            kind="custom",
        )
        session.add(row)
        await session.flush()
    return row


async def subscribe(session: AsyncSession, profile: BusinessProfile, query: str) -> SourcesState:
    await ensure_profile_sources(session, profile)
    await ensure_catalog(session)
    feed_url = parse_feed_url(query)
    channel = None
    if not feed_url:
        channel = await session.get(Channel, query.strip().lower())
    if channel is not None and not (channel.meta or {}).get("feed_url"):
        channel = None
    if feed_url:
        channel = await session.get(Channel, rss_channel_id(feed_url))
        if channel is None:
            channel = await _find_channel(session, feed_url)
    if channel is None:
        channel = await _find_channel(session, query)
    if channel is None:
        if feed_url:
            channel = await _custom_rss_channel(session, feed_url)
        else:
            handle = parse_handle(query)
            if handle is None:
                raise LookupError("Укажите @тег, ссылку t.me или URL RSS.")
            channel = await _custom_channel(session, handle)
    source = "custom" if channel.kind == "custom" else "catalog"
    await _add_subscription(session, profile, channel.id, source)
    await session.flush()
    return await sources_state(session, profile)


async def unsubscribe(
    session: AsyncSession, profile: BusinessProfile, channel_id: str
) -> SourcesState:
    await ensure_profile_sources(session, profile)
    await session.execute(
        delete(ProfileChannel).where(
            ProfileChannel.profile_id == profile.id,
            ProfileChannel.channel_id == channel_id,
        )
    )
    await session.flush()
    return await sources_state(session, profile)


async def unsubscribe_all(session: AsyncSession, profile: BusinessProfile) -> SourcesState:
    await ensure_profile_sources(session, profile)
    await session.execute(delete(ProfileChannel).where(ProfileChannel.profile_id == profile.id))
    await session.flush()
    return await sources_state(session, profile)


async def restore_recommended(session: AsyncSession, profile: BusinessProfile) -> SourcesState:
    await ensure_profile_sources(session, profile)
    await ensure_catalog(session)
    await session.execute(delete(ProfileChannel).where(ProfileChannel.profile_id == profile.id))
    for channel_id in await _recommended_ids(session, profile):
        await _add_subscription(session, profile, channel_id, "recommended")
    await session.flush()
    return await sources_state(session, profile)
