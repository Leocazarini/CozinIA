"""Application settings, loaded from environment variables / .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Cozinia backend."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # No default credentials on purpose: a missing DATABASE_URL must fail
    # app startup loudly, never fall back to a known username/password.
    database_url: str
    # Only ever read by the test suite (never by the running app) — optional
    # here so the app itself doesn't need it to start; the test suite fails
    # clearly on its own if it's actually missing when tests run.
    test_database_url: str | None = None
    openrouter_api_key: str = ""
    ai_model: str = "anthropic/claude-sonnet-5"


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings instance."""
    return Settings()
