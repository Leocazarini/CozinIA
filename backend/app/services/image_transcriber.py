"""Reads recipe text out of uploaded photos using a vision model on
OpenRouter.

This is the image flow's counterpart to `scraper.fetch_and_extract_text`:
both produce plain text, which `ai_extractor.extract_recipe` then turns into
a structured recipe. Going through text rather than asking a vision model
for structured JSON directly costs one extra call, and buys three things:
the "is this actually a recipe?" contract is reused untouched, the
transcription is kept in `raw_extracted_text` as the only trace of an image
that isn't stored, and it works with vision models regardless of whether
they support structured output.
"""

import base64
import logging
from collections.abc import Sequence

from openai import AsyncOpenAI, OpenAIError

from app.core.config import get_settings
from app.services.ai_extractor import AIRequestError

logger = logging.getLogger(__name__)

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Mirrors the scraper's floor for scraped pages: below this there is not
# enough text for an extraction attempt to be worth making.
_MINIMUM_TRANSCRIPT_LENGTH = 100

_SYSTEM_PROMPT = (
    "You transcribe recipes from photographs — cookbook pages, handwritten cards, "
    "screenshots, package labels.\n\n"
    "All the images you receive are pages or parts of a SINGLE recipe, given in reading "
    "order: transcribe them as one continuous document, not one per image.\n\n"
    "Transcribe the text faithfully and completely, preserving structure: the title, the "
    "ingredient list one per line, the preparation steps in order, and any yield, times or "
    "temperatures. Keep the original language — do not translate. Do not summarise, do not "
    "reformat into your own words, and never invent text that isn't legible in the images. "
    "Ignore anything that isn't part of the recipe (page numbers, headers, unrelated "
    "columns).\n\n"
    "Output only the transcription, as plain text — no commentary, no markdown fences."
)

_USER_INSTRUCTION = "Transcribe the recipe in these images."


class UnreadableImageError(Exception):
    """Raised when the vision model returns no usable text for the given
    images — they are blurry, empty, or not a document at all."""


def _build_client() -> AsyncOpenAI:
    settings = get_settings()
    return AsyncOpenAI(base_url=_OPENROUTER_BASE_URL, api_key=settings.openrouter_api_key)


async def transcribe_images(
    images: Sequence[bytes], *, client: AsyncOpenAI | None = None
) -> str:
    """Send JPEG `images` to the configured vision model and return their
    recipe text as one document.

    The images must already have passed through `image_intake.prepare_images`
    — they are sent as JPEG data URIs, in order, in a single request.

    Raises AIRequestError if the request to the provider fails, and
    UnreadableImageError if the model returns nothing usable.

    `client` is exposed so tests can inject one backed by an
    httpx.MockTransport instead of hitting the real network.
    """
    settings = get_settings()
    active_client = client if client is not None else _build_client()

    try:
        completion = await active_client.chat.completions.create(
            model=settings.ai_vision_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_content(images)},
            ],
        )
    except OpenAIError as error:
        raise AIRequestError(f"OpenRouter vision request failed: {error}") from error

    # A refusal arrives as a null content, which is indistinguishable here
    # from an empty answer — either way there is no text to extract from, and
    # that is what the user needs to be told.
    text = (completion.choices[0].message.content or "").strip()
    if len(text) < _MINIMUM_TRANSCRIPT_LENGTH:
        logger.info("Vision model returned %d characters for %d image(s)", len(text), len(images))
        raise UnreadableImageError(
            f"Transcription was too short to be a recipe ({len(text)} characters)"
        )

    return text


def _build_user_content(images: Sequence[bytes]) -> list[dict]:
    """The instruction followed by one image part per photo, in order — the
    order is what lets the model read a two-page recipe as page 1 then 2."""
    content: list[dict] = [{"type": "text", "text": _USER_INSTRUCTION}]
    for image in images:
        encoded = base64.b64encode(image).decode("ascii")
        content.append(
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
        )
    return content
