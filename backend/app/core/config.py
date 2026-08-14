"""Application settings, loaded from environment variables / .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the CozinIA backend."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # No default credentials on purpose: a missing DATABASE_URL must fail
    # app startup loudly, never fall back to a known username/password.
    database_url: str

    # Signs and verifies login tokens. No default, for the same reason as
    # database_url: a predictable key would let anyone forge a valid session,
    # so a missing JWT_SECRET must stop the app from starting rather than fall
    # back to something guessable. Generate one with `openssl rand -hex 32`.
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    # How long a login stays valid. A week keeps an installed PWA from asking
    # for the password on every use, while still expiring an old token.
    access_token_ttl_minutes: int = 60 * 24 * 7

    # The exact browser origin allowed to call the API (CORS). In production
    # this is the app's own https origin; left unset in dev, where the frontend
    # reaches the API same-origin through the Vite/nginx proxy and a small set
    # of localhost origins is allowed instead. Never a wildcard.
    allowed_origin: str | None = None

    # Only ever read by the test suite (never by the running app) — optional
    # here so the app itself doesn't need it to start; the test suite fails
    # clearly on its own if it's actually missing when tests run.
    test_database_url: str | None = None
    openrouter_api_key: str = ""
    ai_model: str = ""
    
    # Separate from ai_model on purpose: reading recipe photos needs a
    # vision-capable model, and the model chosen for text extraction is not
    # necessarily one. Keeping them apart lets either be swapped alone.
    ai_vision_model: str = ""

    # Separate for the same reason: this one turns a video's noisy narration
    # plus its written description into one clean recipe document, which needs
    # stronger instruction-following on long, messy input than pulling fields
    # out of already-clean text does.
    ai_video_model: str = ""

    # Speech-to-text goes to OpenRouter's /audio/transcriptions endpoint,
    # which only accepts transcription models — a chat model is never valid
    # there, so this cannot share any of the vars above.
    ai_audio_model: str = ""

    # Translates an already-extracted recipe into Brazilian Portuguese and
    # converts its measurements to metric units. Separate from ai_model for
    # the same reason as the others: it needs to follow a fairly long,
    # detailed instruction (translate this, not that; convert these units,
    # not those) rather than just pull fields out of clean text.
    ai_translation_model: str = ""

    # Optional path to a Netscape cookies.txt handed to yt-dlp. Instagram and
    # TikTok are the platforms whose recipes are spoken rather than written —
    # exactly the ones that refuse anonymous requests from a datacenter IP.
    # Empty (the default) keeps yt-dlp anonymous; a real session file is a
    # live credential, so see docs/DOCKER.md before mounting one.
    video_cookies_file: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings instance."""
    return Settings()
