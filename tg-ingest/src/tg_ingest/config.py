import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _split(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    api_id: int = field(default_factory=lambda: int(os.getenv("TG_API_ID", "0") or 0))
    api_hash: str = field(default_factory=lambda: os.getenv("TG_API_HASH", ""))
    phone: str = field(default_factory=lambda: os.getenv("TG_PHONE", ""))
    password: str = field(default_factory=lambda: os.getenv("TG_2FA_PASSWORD", ""))
    session: Path = field(
        default_factory=lambda: Path(os.getenv("TG_SESSION", "state/tg_ingest"))
    )
    channels: tuple[str, ...] = field(
        default_factory=lambda: _split(os.getenv("TG_CHANNELS", ""))
    )

    backend_url: str = field(
        default_factory=lambda: os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    )
    ingest_path: str = field(
        default_factory=lambda: os.getenv("INGEST_PATH", "/api/ingest/posts")
    )
    channels_path: str = field(
        default_factory=lambda: os.getenv("CHANNELS_PATH", "/api/ingest/channels")
    )
    sync_interval: float = field(
        default_factory=lambda: float(os.getenv("CHANNELS_SYNC_INTERVAL", "60"))
    )
    join_retry_seconds: float = field(
        default_factory=lambda: float(os.getenv("CHANNEL_JOIN_RETRY", "600"))
    )
    join_delay_min: float = field(
        default_factory=lambda: float(os.getenv("JOIN_DELAY_MIN", "30"))
    )
    join_delay_max: float = field(
        default_factory=lambda: float(os.getenv("JOIN_DELAY_MAX", "90"))
    )
    join_batch: int = field(default_factory=lambda: int(os.getenv("JOIN_BATCH", "2")))
    join_daily_limit: int = field(
        default_factory=lambda: int(os.getenv("JOIN_DAILY_LIMIT", "20"))
    )
    join_state: Path = field(
        default_factory=lambda: Path(os.getenv("JOIN_STATE", "state/joins.json"))
    )
    ingest_token: str = field(default_factory=lambda: os.getenv("INGEST_TOKEN", ""))
    timeout: float = field(default_factory=lambda: float(os.getenv("HTTP_TIMEOUT", "30")))
    retries: int = field(default_factory=lambda: int(os.getenv("INGEST_RETRIES", "3")))


def load_settings() -> Settings:
    settings = Settings()
    if not settings.api_id or not settings.api_hash:
        raise SystemExit("TG_API_ID и TG_API_HASH обязательны (получить: https://my.telegram.org)")
    if not settings.ingest_token:
        print("warning: INGEST_TOKEN пуст, эндпоинт бэкенда может быть открыт без секрета")
    return settings
