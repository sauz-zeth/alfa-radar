import logging
import random
import time
from pathlib import Path

import feedparser
import httpx

from back.core.sources import CHANNELS

RSSHUB_URL = "http://localhost:1200/telegram/channel"
AVATAR_DIR = Path(__file__).resolve().parents[1] / "src" / "back" / "static" / "avatars"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=20, follow_redirects=True) as client:
        for index, channel in enumerate(CHANNELS):
            try:
                if not channel.handle:
                    logger.warning("%s: пропуск — у источника нет Telegram handle", channel.id)
                    continue
                if (AVATAR_DIR / f"{channel.id}.jpg").exists():
                    logger.info("%s: уже загружен, пропуск", channel.id)
                    continue
                response = client.get(f"{RSSHUB_URL}/{channel.handle.lstrip('@')}")
                response.raise_for_status()
                image_url = feedparser.parse(response.content).feed.get("image", {}).get("href")
                if not image_url:
                    logger.warning("%s: RSS не содержит feed.image.href", channel.id)
                    continue
                image = client.get(image_url)
                image.raise_for_status()
                if not image.headers.get("content-type", "").startswith("image/"):
                    logger.warning("%s: URL аватара вернул не изображение", channel.id)
                    continue
                (AVATAR_DIR / f"{channel.id}.jpg").write_bytes(image.content)
                logger.info("%s: аватар сохранён", channel.id)
            except Exception as exc:
                logger.warning("%s: пропуск из-за ошибки: %s", channel.id, exc)
            finally:
                if index < len(CHANNELS) - 1:
                    time.sleep(random.uniform(1, 2))


if __name__ == "__main__":
    main()
