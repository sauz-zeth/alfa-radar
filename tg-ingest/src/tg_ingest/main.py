import argparse
import asyncio
import logging
import sys
from typing import Any

import httpx
from telethon import TelegramClient, events

from .backend import send_post
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


async def resolve_channels(
    client: TelegramClient, handles: tuple[str, ...]
) -> list[Any] | None:
    if not handles:
        return None
    chats = []
    for handle in handles:
        try:
            chats.append(await client.get_entity(handle))
        except Exception as exc:
            logger.warning("cannot resolve channel %s: %s", handle, exc)
    if not chats:
        raise SystemExit("Не удалось найти ни одного канала из TG_CHANNELS")
    return chats


async def run(settings: Settings) -> None:
    settings.session.parent.mkdir(parents=True, exist_ok=True)
    client = TelegramClient(str(settings.session), settings.api_id, settings.api_hash)
    await authorize(client, settings)
    me = await client.get_me()
    logger.info("logged in as %s (@%s, id=%s)", me.first_name, me.username, me.id)

    chats = await resolve_channels(client, settings.channels)
    if chats:
        logger.info("listening to %s configured channels", len(chats))
    else:
        logger.info("TG_CHANNELS пуст: слушаю все каналы, на которые подписан аккаунт")

    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=settings.timeout) as http:

        @client.on(events.NewMessage(chats=chats))
        async def handler(event: events.NewMessage.Event) -> None:
            if not event.is_channel or event.is_group:
                return
            text = event.raw_text or ""
            if not text.strip():
                return
            chat = await event.get_chat()
            payload = build_payload(
                text=text,
                chat_id=getattr(chat, "id", event.chat_id),
                chat_title=getattr(chat, "title", None),
                username=getattr(chat, "username", None),
                message_id=event.message.id,
                published_at=event.message.date,
            )
            await send_post(http, settings, payload)

        await client.run_until_disconnected()


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
