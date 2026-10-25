import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _split(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _state_dir() -> Path:
    return Path(os.getenv("TG_STATE_DIR", "state"))


def _session_path() -> Path:
    value = os.getenv("TG_SESSION", "").strip()
    return Path(value) if value else _state_dir() / "tg_ingest"


def _join_state_path() -> Path:
    value = os.getenv("JOIN_STATE", "").strip()
    return Path(value) if value else _state_dir() / "joins.json"


@dataclass(frozen=True)
class Settings:
    api_id: int = field(default_factory=lambda: int(os.getenv("TG_API_ID", "0") or 0))
    api_hash: str = field(default_factory=lambda: os.getenv("TG_API_HASH", ""))
    phone: str = field(default_factory=lambda: os.getenv("TG_PHONE", ""))
    password: str = field(default_factory=lambda: os.getenv("TG_2FA_PASSWORD", ""))
    state_dir: Path = field(default_factory=_state_dir)
    session: Path = field(default_factory=_session_path)
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
        default_factory=lambda: float(os.getenv("JOIN_DELAY_MIN", "3"))
    )
    join_delay_max: float = field(
        default_factory=lambda: float(os.getenv("JOIN_DELAY_MAX", "8"))
    )
    join_batch: int = field(default_factory=lambda: int(os.getenv("JOIN_BATCH", "5")))
    join_daily_limit: int = field(
        default_factory=lambda: int(os.getenv("JOIN_DAILY_LIMIT", "0"))
    )
    avatar_batch: int = field(default_factory=lambda: int(os.getenv("AVATAR_BATCH", "3")))
    join_state: Path = field(default_factory=_join_state_path)
    ingest_token: str = field(default_factory=lambda: os.getenv("INGEST_TOKEN", ""))
    setup_enabled: bool = field(
        default_factory=lambda: os.getenv("SETUP_ENABLED", "true").lower()
        in {"1", "true", "yes", "on"}
    )
    setup_host: str = field(default_factory=lambda: os.getenv("SETUP_HOST", "127.0.0.1"))
    setup_port: int = field(default_factory=lambda: int(os.getenv("SETUP_PORT", "8081")))
    setup_timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("SETUP_TIMEOUT_SECONDS", "900"))
    )
    timeout: float = field(default_factory=lambda: float(os.getenv("HTTP_TIMEOUT", "30")))
    retries: int = field(default_factory=lambda: int(os.getenv("INGEST_RETRIES", "3")))


def load_settings() -> Settings:
    settings = Settings()
    if not settings.api_id or not settings.api_hash:
        raise SystemExit("TG_API_ID и TG_API_HASH обязательны (получить: https://my.telegram.org)")
    if not settings.ingest_token:
        print("warning: INGEST_TOKEN пуст, эндпоинт бэкенда может быть открыт без секрета")
    return settings
