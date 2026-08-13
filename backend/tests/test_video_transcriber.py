"""Specifications for turning a video's material into one clean recipe
document.

A video's recipe arrives in two halves that neither the scraper nor the photo
door ever has to deal with: quantities written in the description, method
spoken out loud in a transcript with no punctuation and mis-heard words. This
is the pass that merges them, so that what reaches `extract_recipe` is the
same kind of input the other two doors hand it — which is what lets the whole
"is this actually a recipe?" contract be reused untouched.

All tests mock the HTTP layer (httpx.MockTransport) — no real OpenRouter calls
are made.
"""

import json

import httpx
import pytest
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.services.ai_extractor import AIRequestError
from app.services.video_source import AudioClip, NoVideoTextError, SpeechSource, VideoMaterial
from app.services.video_transcriber import UnreadableVideoError, transcribe_video

NARRATION = (
    "oi gente hoje eu vou ensinar o bolo de cenoura da minha vó "
    "bate tudo no liquidificador e leva ao forno a 180 graus por 40 minutos"
)

DESCRIPTION = (
    "INGREDIENTES\n3 cenouras médias\n3 ovos\n2 xícaras de açúcar\n"
    "1 xícara de óleo\n2 xícaras de farinha de trigo"
)

RECIPE_DOCUMENT = (
    "Bolo de cenoura da vovó\n\n"
    "3 cenouras médias\n3 ovos\n2 xícaras de açúcar\n1 xícara de óleo\n"
    "2 xícaras de farinha de trigo\n\n"
    "1. Bata as cenouras, os ovos e o açúcar no liquidificador.\n"
    "2. Leve ao forno a 180 graus por 40 minutos."
)

AUDIO = AudioClip(data=b"fake-opus-audio-bytes", audio_format="opus")


def _material(**overrides: object) -> VideoMaterial:
    fields: dict = {
        "title": "BOLO DE CENOURA DA VOVÓ",
        "uploader": "Cozinha da Vovó",
        "description": DESCRIPTION,
        "caption_transcript": NARRATION,
        "speech_source": SpeechSource.AUTOMATIC_CAPTIONS,
        "audio": None,
    }
    return VideoMaterial(**{**fields, **overrides})


def _chat_completion_response(content: str | None) -> dict:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1_700_000_000,
        "model": "anthropic/claude-sonnet-5",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": content, "refusal": None},
            }
        ],
    }


def _client_returning(content: str | None) -> tuple[AsyncOpenAI, list[httpx.Request]]:
    """A client answering with `content`, plus the list of requests it
    received (so tests can inspect what was sent)."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=_chat_completion_response(content))

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return AsyncOpenAI(api_key="test-key", http_client=http_client), requests


def _failing_client(exception: httpx.HTTPError) -> AsyncOpenAI:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exception

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return AsyncOpenAI(api_key="test-key", http_client=http_client)


def _user_message(request: httpx.Request) -> str:
    payload = json.loads(request.content)
    return next(message["content"] for message in payload["messages"] if message["role"] == "user")


async def _never_transcribes(clip: AudioClip) -> str:
    raise AssertionError("the audio should not have been transcribed")


async def test_given_a_videos_material_when_transcribing_then_returns_a_clean_recipe_document() -> (
    None
):
    """Given the material of a recipe video, when transcribing it, then the
    merged recipe document comes back — what the shared extractor then reads,
    exactly as it reads a scraped page or a transcribed photo."""
    client, _ = _client_returning(RECIPE_DOCUMENT)

    document = await transcribe_video(
        _material(), transcribe_speech=_never_transcribes, client=client
    )

    assert document == RECIPE_DOCUMENT


async def test_given_material_with_a_caption_transcript_when_transcribing_then_the_audio_is_not_used() -> (
    None
):
    """Given material whose narration already came from a caption track, when
    transcribing it, then speech recognition is not called — the caption was
    free, and transcribing on top of it would be paying twice for the same
    words."""
    client, _ = _client_returning(RECIPE_DOCUMENT)

    await transcribe_video(_material(), transcribe_speech=_never_transcribes, client=client)


async def test_given_material_with_only_audio_when_transcribing_then_the_narration_is_recognised() -> (
    None
):
    """Given a Reel with no captions, only audio, when transcribing it, then
    the audio is sent to speech recognition and what it heard reaches the
    model — the path that makes a spoken-only recipe work at all."""
    transcribed: list[AudioClip] = []

    async def transcribe_speech(clip: AudioClip) -> str:
        transcribed.append(clip)
        return NARRATION

    client, requests = _client_returning(RECIPE_DOCUMENT)

    document = await transcribe_video(
        _material(caption_transcript=None, speech_source=None, audio=AUDIO),
        transcribe_speech=transcribe_speech,
        client=client,
    )

    assert transcribed == [AUDIO]
    assert NARRATION in _user_message(requests[0])
    assert document == RECIPE_DOCUMENT


async def test_given_material_from_audio_when_transcribing_then_the_model_is_told_where_it_came_from() -> (
    None
):
    """Given narration that came from speech recognition, when transcribing it,
    then the material says so — how much to trust a transcript is what decides
    whether an odd ingredient is a mis-hearing to repair or a word to keep."""

    async def transcribe_speech(clip: AudioClip) -> str:
        return NARRATION

    client, requests = _client_returning(RECIPE_DOCUMENT)

    await transcribe_video(
        _material(caption_transcript=None, speech_source=None, audio=AUDIO),
        transcribe_speech=transcribe_speech,
        client=client,
    )

    assert str(SpeechSource.AUDIO_TRANSCRIPTION) in _user_message(requests[0])


async def test_given_material_to_transcribe_then_both_halves_of_the_recipe_are_sent() -> None:
    """Given material with a written description and a spoken narration, when
    transcribing it, then both reach the model — a Reel usually writes the
    quantities and says the method, so dropping either loses half the
    recipe."""
    client, requests = _client_returning(RECIPE_DOCUMENT)

    await transcribe_video(_material(), transcribe_speech=_never_transcribes, client=client)

    sent = _user_message(requests[0])
    assert "2 xícaras de açúcar" in sent
    assert "bate tudo no liquidificador" in sent


async def test_given_material_to_transcribe_then_the_configured_video_model_is_used() -> None:
    """Given any transcription request, when it is sent, then it targets the
    video model setting — kept apart from the extraction model so either can
    be swapped alone."""
    client, requests = _client_returning(RECIPE_DOCUMENT)

    await transcribe_video(_material(), transcribe_speech=_never_transcribes, client=client)

    assert json.loads(requests[0].content)["model"] == get_settings().ai_video_model


async def test_given_a_video_whose_audio_holds_no_speech_when_transcribing_then_raises_no_video_text_error() -> (
    None
):
    """Given a video with no captions and audio that turns out to be music
    only, when transcribing it, then NoVideoTextError is raised rather than a
    recipe being invented from a title."""

    async def transcribe_speech(clip: AudioClip) -> str:
        return ""

    client, _ = _client_returning(RECIPE_DOCUMENT)

    with pytest.raises(NoVideoTextError):
        await transcribe_video(
            _material(description=None, caption_transcript=None, speech_source=None, audio=AUDIO),
            transcribe_speech=transcribe_speech,
            client=client,
        )


async def test_given_a_video_whose_only_text_is_a_long_title_when_transcribing_then_raises_no_video_text_error() -> (
    None
):
    """Given a video with a very long title but nothing said and nothing
    written, when transcribing it, then NoVideoTextError is still raised.

    The floor has to be measured on the recipe-bearing text alone. Measured on
    the assembled material instead, the labels and a long title would clear it
    on their own and the check would never fire.
    """

    async def transcribe_speech(clip: AudioClip) -> str:
        return ""

    client, _ = _client_returning(RECIPE_DOCUMENT)

    with pytest.raises(NoVideoTextError):
        await transcribe_video(
            _material(
                title="RECEITA " * 40,
                description=None,
                caption_transcript=None,
                speech_source=None,
                audio=AUDIO,
            ),
            transcribe_speech=transcribe_speech,
            client=client,
        )


async def test_given_a_video_that_is_not_a_recipe_when_transcribing_then_raises_unreadable_video_error() -> (
    None
):
    """Given a video with no recipe in it — a restaurant review, an unboxing —
    when transcribing it, then the model says so in one short line and that
    becomes an UnreadableVideoError.

    One of two legitimate ways a non-recipe video is refused, and the cheaper
    one: it saves the extraction call entirely. The other is the model writing
    a long explanation, which clears the floor and is then refused by the
    shared extractor as not a recipe.
    """
    client, _ = _client_returning("Esse vídeo não tem uma receita.")

    with pytest.raises(UnreadableVideoError):
        await transcribe_video(_material(), transcribe_speech=_never_transcribes, client=client)


async def test_given_the_model_returns_nothing_when_transcribing_then_raises_unreadable_video_error() -> (
    None
):
    """Given the model answering with no content at all (an empty message or a
    refusal), when transcribing, then an UnreadableVideoError is raised."""
    client, _ = _client_returning(None)

    with pytest.raises(UnreadableVideoError):
        await transcribe_video(_material(), transcribe_speech=_never_transcribes, client=client)


async def test_given_the_request_fails_when_transcribing_then_raises_ai_request_error() -> None:
    """Given the request to OpenRouter failing outright, when transcribing,
    then an AIRequestError is raised — the same exception the other two doors
    raise, so the API layer already answers it."""
    client = _failing_client(httpx.ConnectError("connection refused"))

    with pytest.raises(AIRequestError):
        await transcribe_video(_material(), transcribe_speech=_never_transcribes, client=client)


async def test_given_any_video_pass_when_sent_then_it_carries_an_explicit_read_timeout() -> None:
    """Given any video pass, when it is sent, then it carries a read timeout of
    its own.

    The one assertion in this suite coupled to an httpx internal, and it earns
    it: this call takes the largest inputs in the app, so it is the one that
    can actually reach the SDK's 600-second default — long after the browser,
    any proxy and the user have given up.
    """
    client, requests = _client_returning(RECIPE_DOCUMENT)

    await transcribe_video(_material(), transcribe_speech=_never_transcribes, client=client)

    timeout = requests[0].extensions["timeout"]
    assert timeout["read"] is not None
    assert timeout["read"] < 600
