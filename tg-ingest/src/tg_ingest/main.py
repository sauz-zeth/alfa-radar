import argparse
import asyncio
import logging
import sys
from contextlib import suppress

import httpx
from telethon import TelegramClient, events

from .backend import send_post
from .channels import ChannelRegistry
from .config import Settings, load_settings
from .payload import build_payload

logger = logging.getLogger("tg_ingest")


async def authorize(client: TelegramClient, settings: Settings) -> None:
    await client.connect()
    if await client.is_user_authorized():
        return
    if not settings.phone:
        raise SystemExit("Сессия не авторизована. Укажите TG_PHONE и запустите вход заново.")
    if settings.password:
        await client.start(phone=settings.phone, password=settings.password)
    else:
        await client.start(phone=settings.phone)


async def sync_loop(
    registry: ChannelRegistry, http: httpx.AsyncClient, interval: float
) -> None:
    while True:
        try:
            await registry.sync(http)
        except Exception as exc:
            logger.warning("channel sync failed: %s", exc)
        await asyncio.sleep(interval)


async def run(settings: Settings) -> None:
    settings.session.parent.mkdir(parents=True, exist_ok=True)
    client = TelegramClient(str(settings.session), settings.api_id, settings.api_hash)
    await authorize(client, settings)
    me = await client.get_me()
    logger.info("logged in as %s (@%s, id=%s)", me.first_name, me.username, me.id)

    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=settings.timeout) as http:
        registry = ChannelRegistry(client, settings)
        await registry.load_dialogs()
        await registry.sync(http, join=False)
        logger.info("active channels: %s", len(registry.active_ids))
        if not registry.active_ids:
            logger.warning(
                "нет активных каналов: подпишитесь на источники в бэкенде или задайте TG_CHANNELS"
            )
        sync_task = asyncio.create_task(sync_loop(registry, http, settings.sync_interval))

        @client.on(events.NewMessage())
        async def handler(event: events.NewMessage.Event) -> None:
            if not event.is_channel or event.is_group:
                return
            chat = await event.get_chat()
            if getattr(chat, "id", None) not in registry.active_ids:
                return
            text = event.raw_text or ""
            if not text.strip():
                return
            payload = build_payload(
                text=text,
                chat_id=getattr(chat, "id", event.chat_id),
                chat_title=getattr(chat, "title", None),
                username=getattr(chat, "username", None),
                message_id=event.message.id,
                published_at=event.message.date,
            )
            await send_post(http, settings, payload)

        try:
            await client.run_until_disconnected()
        finally:
            sync_task.cancel()
            with suppress(asyncio.CancelledError):
                await sync_task


async def login(settings: Settings) -> None:
    settings.session.parent.mkdir(parents=True, exist_ok=True)
    client = TelegramClient(str(settings.session), settings.api_id, settings.api_hash)
    try:
        await authorize(client, settings)
        me = await client.get_me()
        logger.info("session ready: %s (@%s)", me.first_name, me.username)
    finally:
        await client.disconnect()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="Telegram selfbot -> backend ingest")
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=("login", "run"),
        help="login: create/check the session file, run: listen for new channel posts",
    )
    args = parser.parse_args()

    settings = load_settings()
    command = login if args.command == "login" else run
    try:
        asyncio.run(command(settings))
    except KeyboardInterrupt:
        sys.exit(0)
