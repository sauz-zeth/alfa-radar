from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Alfa Future News Analytics"
    environment: str = "local"
    api_prefix: str = "/api"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/alfafuture"
    database_echo: bool = False

    jwt_secret: str = "change-me-in-production-use-at-least-32-bytes"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:8080"

    # LLM layer. See back/README.md, section "LLM layer".
    llm_provider: str = "stub"  # stub | openai
    llm_base_url: str = "https://changellenge.up.railway.app/v1"
    llm_api_key: str = ""
    llm_model: str = "qwen/qwen3.6-35b-a3b"
    llm_fast_model: str = "google/gemma-4-26b-a4b-it"
    # Role aliases for the news pipeline. Empty value falls back to the legacy names:
    # weak -> llm_fast_model, strong -> llm_model.
    llm_weak_model: str = ""
    llm_strong_model: str = ""
    llm_timeout_seconds: float = 60.0
    llm_temperature: float = 0.2
    # The agent may use the LLM; ML-ish helpers (categories, counterparties, reporting)
    # stay deterministic until explicitly enabled.
    llm_agent_enabled: bool = True
    llm_ml_enabled: bool = False

    # Optional shared secret for internal ingestion endpoints (X-Ingest-Token).
    ingest_token: str = ""

    # Comma-separated RSS/Atom feeds polled by scripts/ingest_rss.py.
    rss_feeds: str = ""
    # Background poller for RSS sources subscribed by users.
    rss_poll_enabled: bool = True
    rss_poll_interval_seconds: int = 300
    rss_poll_initial_delay_seconds: float = 20

    data_dir: Path = Path("data")
    seed_company_limit: int = 0
    seed_with_payments: bool = True

    demo_login: str = "demo"
    demo_password: str = "demo"
    demo_full_login: str = "demo_full"
    demo_full_password: str = "demo"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def weak_model(self) -> str:
        return self.llm_weak_model or self.llm_fast_model

    @property
    def strong_model(self) -> str:
        return self.llm_strong_model or self.llm_model

    @property
    def rss_feed_list(self) -> list[str]:
        return [item.strip() for item in self.rss_feeds.split(",") if item.strip()]

    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("+asyncpg", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()
