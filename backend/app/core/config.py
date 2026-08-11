"""Application settings, loaded from environment variables / .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Cozinia backend."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://cozinia:cozinia@localhost:5432/cozinia"
    test_database_url: str = "postgresql+asyncpg://cozinia:cozinia@localhost:5432/cozinia_test"
    openrouter_api_key: str = ""
    ai_model: str = "anthropic/claude-sonnet-5"


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings instance."""
    return Settings()
