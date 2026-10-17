from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "alfa-hackathon-back"
    debug: bool = False
    api_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/alfafuture"

    litellm_base_url: str | None = None
    litellm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_fast_model: str = "gpt-4o-mini"
    llm_retries: int = 1
    llm_timeout: float = 60.0

    classifier_model: str = "ai-forever/ruBert-base"
    category_thresholds: dict[str, float] = Field(default_factory=dict)
    embedder_model: str = "intfloat/multilingual-e5-base"
    embedding_dim: int = 768

    cluster_threshold: float = 0.85
    cluster_window_hours: int = 2
    prescore_tau: float = 0.5
    max_llm_calls_per_hour: int = 20

    chain_threshold: float = 0.75
    chain_top_k: int = 3
    chain_close_after_days: int = 14
    push_daily_limit: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
