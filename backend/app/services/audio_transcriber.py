"""Transcribes a video's audio into text, using speech-to-text on OpenRouter.

The other half of how the video door reads narration: `video_source` prefers a
caption track the platform already publishes, and falls through to here for
the videos that publish none — most of Instagram and TikTok, which is exactly
where a recipe is spoken instead of written.

OpenRouter's /audio/transcriptions endpoint is OpenAI-compatible and lives at
the base url the app already talks to, so this reuses the same provider and
the same key as extraction; it only needs a transcription model rather than a
chat one, which is why it has a setting of its own.
"""

import logging
from collections.abc import Awaitable, Callable

from openai import AsyncOpenAI, OpenAIError

from app.core.config import get_settings
from app.services.ai_extractor import AIRequestError
from app.services.video_source import AudioClip

logger = logging.getLogger(__name__)

TranscribeAudioFn = Callable[[AudioClip], Awaitable[str]]

# What the endpoint takes. Notably absent: opus — ffmpeg produces it happily
# and the endpoint rejects it with a bare "Provider returned 400" that says
# nothing about the format, so the audio download's own format is checked
# against this list by a test rather than discovered in production.
TRANSCRIBABLE_AUDIO_FORMATS = frozenset({"wav", "mp3", "flac", "m4a", "ogg", "webm", "aac"})

# Duplicated from ai_extractor and image_transcriber rather than shared: see
# the note in video_transcriber about chore/extract-openrouter-client.
_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# The SDK defaults to 600 seconds, which is longer than any browser, proxy or
# person waits — a hung transcription would hold the request open long after
# the user gave up on it.
_TIMEOUT_SECONDS = 180.0

# The app is Portuguese, and short clips with music over them are where
# language detection guesses wrong — a recipe transcribed as the wrong
# language is unusable. Stating it costs videos in other languages, which is a
# trade this layer makes knowingly.
_LANGUAGE = "pt"


def _build_client() -> AsyncOpenAI:
    settings = get_settings()
    return AsyncOpenAI(base_url=_OPENROUTER_BASE_URL, api_key=settings.openrouter_api_key)


async def transcribe_audio(clip: AudioClip, *, client: AsyncOpenAI | None = None) -> str:
    """Return what is said in `clip`, or empty text when nothing is.

    Empty is not an error here: a video whose audio is only music still has
    its written description to fall back on, so whether there is enough to
    work with is the caller's call to make.

    Raises AIRequestError if the request to the provider fails.

    `client` is exposed so tests can inject one backed by an
    httpx.MockTransport instead of hitting the real network.
    """
    settings = get_settings()
    active_client = client if client is not None else _build_client()

    try:
        transcription = await active_client.audio.transcriptions.create(
            model=settings.ai_audio_model,
            file=(f"audio.{clip.audio_format}", clip.data),
            language=_LANGUAGE,
            timeout=_TIMEOUT_SECONDS,
        )
    except OpenAIError as error:
        raise AIRequestError(f"OpenRouter transcription request failed: {error}") from error

    text = (transcription.text or "").strip()
    logger.info("Transcribed %d bytes of audio into %d characters", len(clip.data), len(text))
    return text
