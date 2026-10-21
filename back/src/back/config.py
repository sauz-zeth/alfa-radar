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
    llm_timeout_seconds: float = 60.0
    llm_temperature: float = 0.2

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
    def sync_database_url(self) -> str:
        return self.database_url.replace("+asyncpg", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()
