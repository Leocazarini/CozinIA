"""Specifications for transcribing a video's audio into text.

The video door reads a caption track when the platform publishes one; this is
the other half, for the videos that publish none — most of Instagram and
TikTok, which is exactly where a recipe is spoken rather than written.

It goes to OpenRouter's speech-to-text endpoint, so it reuses the provider,
the base url and the key already used for extraction, and needs a
transcription model rather than a chat one. All tests mock the HTTP layer
(httpx.MockTransport) — no real OpenRouter calls are made.
"""

import httpx
import pytest
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.services import video_source
from app.services.ai_extractor import AIRequestError
from app.services.audio_transcriber import TRANSCRIBABLE_AUDIO_FORMATS, transcribe_audio
from app.services.video_source import AudioClip

CLIP = AudioClip(data=b"fake-mp3-audio-bytes", audio_format="mp3")

NARRATION = (
    "oi gente hoje eu vou ensinar o bolo de cenoura da minha vó "
    "vamos precisar de três cenouras médias três ovos e duas xícaras de açúcar "
    "bate tudo no liquidificador e leva ao forno a 180 graus por 40 minutos"
)


def _client_returning(text: str) -> tuple[AsyncOpenAI, list[httpx.Request]]:
    """A client answering with `text`, plus the list of requests it received."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"text": text})

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return AsyncOpenAI(api_key="test-key", http_client=http_client), requests


def _failing_client(exception: httpx.HTTPError) -> AsyncOpenAI:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exception

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return AsyncOpenAI(api_key="test-key", http_client=http_client)


def test_given_the_audio_we_produce_when_checking_its_format_then_the_endpoint_accepts_it() -> None:
    """Given the format the audio download produces, when checking it against
    what the transcription endpoint takes, then it is on the accepted list.

    Found the hard way: the first choice here was opus, which ffmpeg produces
    happily and the endpoint rejects with a bare "Provider returned 400" —
    nothing in the failure says the format was the problem. This test is the
    tripwire so that a future format change fails locally instead of in
    production.
    """
    assert video_source._AUDIO_FORMAT in TRANSCRIBABLE_AUDIO_FORMATS


async def test_given_a_videos_audio_when_transcribing_then_returns_what_was_said() -> None:
    """Given the audio of a recipe video, when transcribing it, then the spoken
    narration comes back as text — ready to be merged with the video's written
    description into one recipe document."""
    client, _ = _client_returning(NARRATION)

    text = await transcribe_audio(CLIP, client=client)

    assert text == NARRATION


async def test_given_audio_to_transcribe_then_the_configured_transcription_model_is_used() -> None:
    """Given any transcription request, when it is sent, then it targets the
    audio model setting — the speech-to-text endpoint accepts transcription
    models only, so neither of the chat model settings would work here."""
    client, requests = _client_returning(NARRATION)

    await transcribe_audio(CLIP, client=client)

    assert get_settings().ai_audio_model.encode() in requests[0].content


async def test_given_audio_to_transcribe_then_it_is_sent_to_the_transcription_endpoint() -> None:
    """Given any transcription request, when it is sent, then it goes to the
    speech-to-text endpoint with the clip attached, not to chat completions."""
    client, requests = _client_returning(NARRATION)

    await transcribe_audio(CLIP, client=client)

    assert requests[0].url.path.endswith("/audio/transcriptions")
    assert CLIP.data in requests[0].content


async def test_given_a_video_in_portuguese_when_transcribing_then_the_language_is_stated() -> None:
    """Given audio to transcribe, when the request is sent, then it names the
    language.

    Short clips with music over them are where speech recognition guesses the
    language wrong, and a recipe transcribed as the wrong language is unusable.
    The app is Portuguese, so saying so is the safer default — at the cost of
    videos in other languages, which is a trade this layer accepts knowingly.
    """
    client, requests = _client_returning(NARRATION)

    await transcribe_audio(CLIP, client=client)

    assert b"pt" in requests[0].content


async def test_given_audio_with_no_speech_when_transcribing_then_returns_empty_text() -> None:
    """Given a clip with nothing said in it — music over a silent montage —
    when transcribing it, then empty text comes back rather than an error.

    Deciding there is too little to work with belongs to the caller, which
    still has the video's written description as a second source.
    """
    client, _ = _client_returning("   ")

    assert await transcribe_audio(CLIP, client=client) == ""


async def test_given_the_request_fails_when_transcribing_then_raises_ai_request_error() -> None:
    """Given the request to OpenRouter failing outright, when transcribing,
    then an AIRequestError is raised — the same exception the other two doors
    raise, so the API layer already answers it."""
    client = _failing_client(httpx.ConnectError("connection refused"))

    with pytest.raises(AIRequestError):
        await transcribe_audio(CLIP, client=client)


async def test_given_any_transcription_request_when_sent_then_it_carries_an_explicit_read_timeout() -> (
    None
):
    """Given any transcription request, when it is sent, then it carries a read
    timeout of its own.

    The one assertion in this suite coupled to an httpx internal, and it earns
    it: the SDK's default is 600 seconds, which is longer than any browser,
    proxy or person will wait, so a hung transcription would hold a request
    open long after the user gave up on it.
    """
    client, requests = _client_returning(NARRATION)

    await transcribe_audio(CLIP, client=client)

    timeout = requests[0].extensions["timeout"]
    assert timeout["read"] is not None
    assert timeout["read"] < 600
