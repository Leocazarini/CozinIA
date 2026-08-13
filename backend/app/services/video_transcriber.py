"""Turns a video's material into one clean recipe document, using a model on
OpenRouter.

This is the video flow's counterpart to `image_transcriber.transcribe_images`,
and it exists for the same reason: every door produces plain text, and
`ai_extractor.extract_recipe` structures it, so the "is this actually a
recipe?" contract is reused untouched and `raw_extracted_text` stays readable.

A video makes that step do more work than the other doors need. Its recipe
arrives in two halves — quantities written in the description, method spoken
in a transcript with no punctuation, mis-heard words and "[Música]" — and
neither half is a recipe on its own. Merging them here means the extractor
receives exactly the kind of input it already receives from a scraped page.

There are deliberately two ways a video with no recipe in it gets refused:
the model answers in one short line, which falls under the floor below and
raises UnreadableVideoError (cheaper — it saves the extraction call), or it
writes a longer explanation, which clears the floor and is refused by the
shared extractor as not a recipe. Both are correct; don't "fix" the short
answer instruction in the prompt without knowing it reroutes that.
"""

import logging

from openai import AsyncOpenAI, OpenAIError

from app.core.config import get_settings
from app.services.ai_extractor import AIRequestError
from app.services.audio_transcriber import TranscribeAudioFn, transcribe_audio
from app.services.video_source import (
    MINIMUM_VIDEO_TEXT_LENGTH,
    NoVideoTextError,
    SpeechSource,
    VideoMaterial,
    render_material,
)

logger = logging.getLogger(__name__)

# Duplicated from ai_extractor and image_transcriber, which already carry a
# copy each. Extracting all four would mean editing two modules that carry two
# shipped doors, inside a feature branch, for no behaviour change — so it is
# its own branch: chore/extract-openrouter-client.
_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Mirrors the floor the scraper and the photo door apply: below this there is
# not enough text for an extraction attempt to be worth making.
_MINIMUM_DOCUMENT_LENGTH = 100

# This call takes the largest inputs in the app, so it is the one that can
# actually reach the SDK's 600-second default read timeout — longer than any
# browser or proxy will wait, and far longer than a user will.
_TIMEOUT_SECONDS = 120.0

_SYSTEM_PROMPT = (
    "You reconstruct one recipe from the material of a single cooking video: its title, the "
    "description or caption written by the author, and a transcript of the narration — either "
    "the video's captions or speech recognition of its audio.\n\n"
    "The recipe is usually split across those parts. The written description tends to carry "
    "the ingredient list with exact quantities; the narration tends to carry the method, the "
    "pan size, the oven temperature and the timings. Merge them into one recipe. Where the two "
    "disagree, prefer the written description for quantities and the narration for the steps.\n\n"
    "The narration is automatic transcription of informal speech: no punctuation or sentence "
    "breaks, and mis-heard ingredient names and numbers. It also contains material that is not "
    "part of the recipe — greetings, \"[Música]\" and other sound markers, requests to "
    "subscribe, sponsor reads, small talk. Ignore all of that. Where a mis-hearing is "
    "unambiguous from the cooking context, write the ingredient the cook clearly meant; where "
    "it is not, keep the ingredient without a quantity rather than guessing one.\n\n"
    "Never invent a quantity, a temperature, a time or a yield that isn't stated in the "
    "material. An ingredient mentioned with no amount is written with no amount — that is a "
    "correct answer. A plausible-looking \"2 xícaras\" that nobody said is not.\n\n"
    "Write the result as one clean recipe document in the language spoken in the video: the "
    "title on the first line, then the ingredients one per line, then the preparation steps in "
    "order, then any yield, times or temperatures that were actually stated. Do not translate, "
    "and do not add advice or commentary of your own.\n\n"
    "If the material does not describe a recipe at all — no ingredients and no preparation "
    "steps, e.g. a restaurant review or a kitchen-gadget unboxing — do not invent one: answer "
    "with a single short line saying so.\n\n"
    "Output only the recipe document, as plain text — no commentary, no markdown fences."
)


class UnreadableVideoError(Exception):
    """Raised when the model returns nothing usable for a video's material —
    there was no recipe in it to reconstruct."""


def _build_client() -> AsyncOpenAI:
    settings = get_settings()
    return AsyncOpenAI(base_url=_OPENROUTER_BASE_URL, api_key=settings.openrouter_api_key)


async def transcribe_video(
    material: VideoMaterial,
    *,
    transcribe_speech: TranscribeAudioFn = transcribe_audio,
    client: AsyncOpenAI | None = None,
) -> str:
    """Merge `material` into one recipe document and return it.

    Narration comes from the caption track when `video_source` found one, and
    from speech recognition of the audio when it didn't.

    Raises NoVideoTextError if the video yields no recipe-bearing text at all,
    AIRequestError if the request to the provider fails, and
    UnreadableVideoError if the model returns nothing usable.

    `transcribe_speech` and `client` are exposed so tests can inject their own
    instead of hitting the real network.
    """
    settings = get_settings()
    active_client = client if client is not None else _build_client()

    speech, speech_source = await _read_narration(material, transcribe_speech)
    _assert_enough_to_work_with(material, speech)

    try:
        completion = await active_client.chat.completions.create(
            model=settings.ai_video_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": render_material(
                        material, speech=speech, speech_source=speech_source
                    ),
                },
            ],
            timeout=_TIMEOUT_SECONDS,
        )
    except OpenAIError as error:
        raise AIRequestError(f"OpenRouter video request failed: {error}") from error

    # A refusal arrives as null content, indistinguishable here from an empty
    # answer — either way there is no recipe to hand on, and that is what the
    # user needs to be told.
    document = (completion.choices[0].message.content or "").strip()
    if len(document) < _MINIMUM_DOCUMENT_LENGTH:
        logger.info("Video model returned %d characters for %s", len(document), material.title)
        raise UnreadableVideoError(
            f"The video did not yield a recipe ({len(document)} characters)"
        )

    return document


async def _read_narration(
    material: VideoMaterial, transcribe_speech: TranscribeAudioFn
) -> tuple[str | None, SpeechSource | None]:
    """The narration and where it came from: the caption track when the
    platform published one, speech recognition of the audio when it didn't."""
    if material.caption_transcript:
        return material.caption_transcript, material.speech_source
    if material.audio is not None:
        return await transcribe_speech(material.audio), SpeechSource.AUDIO_TRANSCRIPTION
    return None, None


def _assert_enough_to_work_with(material: VideoMaterial, speech: str | None) -> None:
    """Refuse a video that yields no recipe-bearing text.

    Measured on the description and the narration only, never on the rendered
    material: the labels plus a long title clear this floor by themselves, so
    checking the assembled string would make the check unreachable.
    """
    content = f"{material.description or ''}{speech or ''}"
    if len(content) < MINIMUM_VIDEO_TEXT_LENGTH:
        raise NoVideoTextError("The video has no captions, speech or description to read")
