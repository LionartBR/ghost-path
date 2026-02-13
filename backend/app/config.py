"""Application Configuration — environment-driven settings via pydantic-settings.

Invariants:
    - All secrets come from environment variables (never hardcoded)
    - get_settings() is cached (lru_cache) — single instance per process

Design Decisions:
    - pydantic-settings over raw os.environ: validation, type coercion, .env file support (ADR: developer UX)
    - Defaults provided for all non-secret settings: works out-of-the-box with docker-compose
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # Database
    database_url: str = (
        "postgresql+asyncpg://triz:triz@db:5432/triz"
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def convert_postgres_url(cls, v: str) -> str:
        """Railway provides postgresql:// but asyncpg needs postgresql+asyncpg://."""
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Anthropic
    anthropic_api_key: str = "sk-ant-placeholder"
    anthropic_max_retries: int = 3
    anthropic_timeout_seconds: int = 300
    anthropic_base_delay_ms: int = 1000
    anthropic_max_delay_ms: int = 60_000

    # Agent
    agent_max_iterations: int = 50
    agent_model: str = "claude-opus-4-6"

    # Context window — 1M beta (requires Anthropic tier 4)
    # ADR: opt-in via env var. Without tier 4, falls back to 200K automatically.
    anthropic_context_1m: bool = True

    # API
    cors_origins: list[str] = ["http://localhost:5173"]

    # Observability
    log_level: str = "INFO"
    log_format: str = "json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
