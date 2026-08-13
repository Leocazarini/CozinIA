"""Specifications for reading a video link into the material a recipe can be
reconstructed from.

This is the video flow's counterpart to the scraper: it produces what the
model pass then turns into a recipe document. A video carries its recipe in
two places — the description the author wrote, and what is said out loud — so
the material carries both, preferring a caption track when the platform
publishes one and falling back to the video's audio when it doesn't.

yt-dlp does its own networking through urllib, so it cannot be intercepted by
httpx.MockTransport: it is injected as a callable instead. The caption
download is ours, so that one uses the transport seam the scraper uses. No
test here touches the real network.
"""

import asyncio
import threading
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest
from yt_dlp.utils import DownloadError

from app.services import video_source
from app.services.video_source import (
    AudioClip,
    NotASingleVideoError,
    NoVideoTextError,
    SpeechSource,
    UnsupportedVideoUrlError,
    VideoAccessBlockedError,
    VideoTooLongError,
    VideoUnavailableError,
    fetch_video,
    render_material,
)

FIXTURES = Path(__file__).parent / "fixtures"
AUTO_CAPTIONS = (FIXTURES / "youtube_auto_captions.vtt").read_text(encoding="utf-8")
HUMAN_SUBTITLES = (FIXTURES / "youtube_subtitles.vtt").read_text(encoding="utf-8")

VIDEO_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
AUTO_CAPTION_URL = "https://www.youtube.com/api/timedtext?fmt=vtt&kind=asr"
HUMAN_CAPTION_URL = "https://www.youtube.com/api/timedtext?fmt=vtt&kind=uploader"

DESCRIPTION = (
    "INGREDIENTES\n"
    "3 cenouras médias\n"
    "3 ovos\n"
    "2 xícaras de açúcar\n"
    "1 xícara de óleo\n"
    "2 xícaras de farinha de trigo\n\n"
    "Inscreva-se no canal e ative o sininho!"
)

AUDIO = AudioClip(data=b"fake-audio-bytes", audio_format="opus")


def _info_dict(**overrides: object) -> dict:
    """The subset of yt-dlp's info dict this app reads, in its real shape.

    The caption track lists json3 before vtt on purpose: the selector has to
    pick by format, not by taking the first entry.
    """
    info: dict = {
        "_type": "video",
        "id": "dQw4w9WgXcQ",
        "title": "BOLO DE CENOURA DA VOVÓ (receita de família)",
        "description": DESCRIPTION,
        "uploader": "Cozinha da Vovó",
        "channel": "Cozinha da Vovó",
        "duration": 372,
        "language": "pt",
        "webpage_url": VIDEO_URL,
        "extractor": "youtube",
        "subtitles": {},
        "automatic_captions": {
            "pt": [
                {"ext": "json3", "url": "https://www.youtube.com/api/timedtext?fmt=json3"},
                {"ext": "vtt", "url": AUTO_CAPTION_URL},
            ]
        },
    }
    return {**info, **overrides}


def _extract_info_returning(info: dict) -> tuple[Callable[[str], dict], list[str]]:
    """A metadata lookup answering with `info`, plus the list recording the
    urls it was asked about (so tests can prove it was never called)."""
    asked: list[str] = []

    def extract_info(url: str) -> dict:
        asked.append(url)
        return info

    return extract_info, asked


def _extract_info_raising(error: Exception) -> Callable[[str], dict]:
    def extract_info(url: str) -> dict:
        raise error

    return extract_info


def _transport_serving(
    captions: dict[str, str],
) -> tuple[httpx.MockTransport, list[httpx.Request]]:
    """A transport answering each caption url in `captions` with its body,
    plus the list of requests it received."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body = captions.get(str(request.url))
        if body is None:
            return httpx.Response(404, text="not found")
        return httpx.Response(200, text=body)

    return httpx.MockTransport(handler), requests


def _download_audio_returning(clip: AudioClip) -> tuple[Callable[[str], AudioClip], list[str]]:
    downloaded: list[str] = []

    def download_audio(url: str) -> AudioClip:
        downloaded.append(url)
        return clip

    return download_audio, downloaded


def _never_downloads(url: str) -> AudioClip:
    raise AssertionError(f"the audio of {url} should not have been downloaded")


async def test_given_a_video_with_captions_when_reading_it_then_the_material_carries_its_metadata_and_transcript() -> (
    None
):
    """Given a recipe video whose platform publishes a caption track, when
    reading it, then the material carries the title, the channel, the written
    description and the transcript of the narration — the two places a video's
    recipe actually lives."""
    extract_info, _ = _extract_info_returning(_info_dict())
    transport, _ = _transport_serving({AUTO_CAPTION_URL: AUTO_CAPTIONS})

    material = await fetch_video(
        VIDEO_URL,
        extract_info=extract_info,
        download_audio=_never_downloads,
        transport=transport,
    )

    assert material.title == "BOLO DE CENOURA DA VOVÓ (receita de família)"
    assert material.uploader == "Cozinha da Vovó"
    assert material.description is not None
    assert "3 cenouras médias" in material.description
    assert material.caption_transcript is not None
    assert "bate tudo no liquidificador" in material.caption_transcript
    assert material.speech_source is SpeechSource.AUTOMATIC_CAPTIONS
    assert material.audio is None


async def test_given_a_video_with_captions_when_reading_it_then_its_audio_is_not_downloaded() -> (
    None
):
    """Given a video that already has a caption track, when reading it, then
    the audio is left alone — reading the published captions costs nothing,
    while downloading and transcribing audio costs time and money."""
    extract_info, _ = _extract_info_returning(_info_dict())
    transport, _ = _transport_serving({AUTO_CAPTION_URL: AUTO_CAPTIONS})
    download_audio, downloaded = _download_audio_returning(AUDIO)

    await fetch_video(
        VIDEO_URL,
        extract_info=extract_info,
        download_audio=download_audio,
        transport=transport,
    )

    assert downloaded == []


async def test_given_a_video_with_no_captions_when_reading_it_then_its_audio_is_downloaded_instead() -> (
    None
):
    """Given a Reel with no caption track — the common case on Instagram and
    TikTok, where the recipe is spoken rather than written — when reading it,
    then the audio comes back in the material so it can be transcribed."""
    extract_info, _ = _extract_info_returning(
        _info_dict(subtitles={}, automatic_captions={})
    )
    transport, requests = _transport_serving({})
    download_audio, downloaded = _download_audio_returning(AUDIO)

    material = await fetch_video(
        VIDEO_URL,
        extract_info=extract_info,
        download_audio=download_audio,
        transport=transport,
    )

    assert material.caption_transcript is None
    assert material.audio == AUDIO
    assert downloaded == [VIDEO_URL]
    assert requests == []


async def test_given_both_uploader_and_automatic_captions_when_reading_then_the_uploader_track_wins() -> (
    None
):
    """Given a video with both hand-written subtitles and automatic captions,
    when reading it, then the hand-written ones are used — they are punctuated
    and accurate, where automatic captions mis-hear ingredient names."""
    extract_info, _ = _extract_info_returning(
        _info_dict(subtitles={"pt": [{"ext": "vtt", "url": HUMAN_CAPTION_URL}]})
    )
    transport, requests = _transport_serving(
        {HUMAN_CAPTION_URL: HUMAN_SUBTITLES, AUTO_CAPTION_URL: AUTO_CAPTIONS}
    )

    material = await fetch_video(
        VIDEO_URL,
        extract_info=extract_info,
        download_audio=_never_downloads,
        transport=transport,
    )

    assert material.speech_source is SpeechSource.UPLOADER_SUBTITLES
    assert material.caption_transcript is not None
    assert "pudim de leite condensado" in material.caption_transcript
    assert [str(request.url) for request in requests] == [HUMAN_CAPTION_URL]


async def test_given_caption_tracks_in_several_formats_when_reading_then_the_vtt_one_is_fetched() -> (
    None
):
    """Given a caption track published in several formats, when reading it,
    then the WebVTT one is fetched — chosen by format, not by being first in
    the list."""
    extract_info, _ = _extract_info_returning(_info_dict())
    transport, requests = _transport_serving({AUTO_CAPTION_URL: AUTO_CAPTIONS})

    await fetch_video(
        VIDEO_URL,
        extract_info=extract_info,
        download_audio=_never_downloads,
        transport=transport,
    )

    assert [str(request.url) for request in requests] == [AUTO_CAPTION_URL]


async def test_given_captions_only_in_another_language_when_reading_then_they_are_still_used() -> (
    None
):
    """Given a video whose only caption track is in another language, when
    reading it, then it is used anyway — a recipe in Spanish is still a
    recipe, and the extractor keeps whatever language it is given."""
    extract_info, _ = _extract_info_returning(
        _info_dict(
            language="es",
            automatic_captions={"es": [{"ext": "vtt", "url": AUTO_CAPTION_URL}]},
        )
    )
    transport, requests = _transport_serving({AUTO_CAPTION_URL: AUTO_CAPTIONS})

    material = await fetch_video(
        VIDEO_URL,
        extract_info=extract_info,
        download_audio=_never_downloads,
        transport=transport,
    )

    assert material.caption_transcript is not None
    assert [str(request.url) for request in requests] == [AUTO_CAPTION_URL]


async def test_given_a_url_that_is_not_http_when_reading_then_raises_unsupported_video_url_error() -> (
    None
):
    """Given a url with a scheme we never fetch, when reading it, then it is
    refused before any lookup happens — nothing should hand a file:// or
    data: url to a library that will go and read it."""
    extract_info, asked = _extract_info_returning(_info_dict())

    for url in ("file:///etc/passwd", "ftp://example.com/video.mp4"):
        with pytest.raises(UnsupportedVideoUrlError):
            await fetch_video(url, extract_info=extract_info, download_audio=_never_downloads)

    assert asked == []


async def test_given_a_url_pointing_at_a_private_address_when_reading_then_raises_unsupported_video_url_error() -> (
    None
):
    """Given a url resolving to a loopback, private or link-local address,
    when reading it, then it is refused before any lookup happens.

    The video door is the one place the app hands a user-supplied url to a
    library that fetches it server-side, so this is what keeps a pasted link
    from reaching localhost or a cloud metadata endpoint.
    """
    extract_info, asked = _extract_info_returning(_info_dict())

    for url in (
        "http://127.0.0.1:8000/health",
        "http://localhost:8000/health",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.5/video.mp4",
        "http://[::1]:8000/health",
    ):
        with pytest.raises(UnsupportedVideoUrlError):
            await fetch_video(url, extract_info=extract_info, download_audio=_never_downloads)

    assert asked == []


async def test_given_a_page_that_is_not_a_video_when_reading_then_raises_unsupported_video_url_error() -> (
    None
):
    """Given a link to an ordinary web page, which yt-dlp accepts and hunts
    for media in rather than rejecting, when reading it, then it is refused —
    a recipe page belongs in the link door, not this one."""
    extract_info, _ = _extract_info_returning(
        _info_dict(
            extractor="generic",
            title="Bolo de cenoura | Panelinha",
            description=None,
            duration=None,
            subtitles={},
            automatic_captions={},
            formats=[],
        )
    )

    with pytest.raises(UnsupportedVideoUrlError):
        await fetch_video(
            "https://panelinha.com.br/receita/bolo-de-cenoura",
            extract_info=extract_info,
            download_audio=_never_downloads,
        )


async def test_given_a_channel_or_playlist_link_when_reading_then_raises_not_a_single_video_error() -> (
    None
):
    """Given a link to a channel, profile or playlist, when reading it, then it
    is refused with its own error — the user has to say which video they
    mean, and enumerating a whole channel is not a thing this app does."""
    extract_info, _ = _extract_info_returning(
        {
            "_type": "playlist",
            "id": "UCabc123",
            "title": "Cozinha da Vovó - Videos",
            "entries": [_info_dict(), _info_dict()],
        }
    )
    transport, requests = _transport_serving({})

    with pytest.raises(NotASingleVideoError):
        await fetch_video(
            "https://www.youtube.com/@cozinhadavovo",
            extract_info=extract_info,
            download_audio=_never_downloads,
            transport=transport,
        )

    assert requests == []


async def test_given_a_private_or_deleted_video_when_reading_then_raises_video_unavailable_error() -> (
    None
):
    """Given a video that is private, deleted or geo-blocked, when reading it,
    then a VideoUnavailableError says so — it is the link that cannot be
    read, not our service that is broken."""
    extract_info = _extract_info_raising(
        DownloadError("ERROR: Private video. Sign in if you've been granted access to this video")
    )

    with pytest.raises(VideoUnavailableError):
        await fetch_video(VIDEO_URL, extract_info=extract_info, download_audio=_never_downloads)


async def test_given_the_platform_refuses_our_server_when_reading_then_raises_video_access_blocked_error() -> (
    None
):
    """Given the platform answering our server with an anti-bot challenge —
    what a datacenter IP gets — when reading it, then the failure is
    distinguished from an unavailable video, because the user's link is fine
    and it is our end that is being refused."""
    for message in (
        "ERROR: [youtube] dQw4w9WgXcQ: Sign in to confirm you're not a bot.",
        "ERROR: [instagram] Requested content is not available, rate-limit reached",
        "ERROR: [tiktok] Unable to download webpage: HTTP Error 429: Too Many Requests",
    ):
        extract_info = _extract_info_raising(DownloadError(message))

        with pytest.raises(VideoAccessBlockedError):
            await fetch_video(
                VIDEO_URL, extract_info=extract_info, download_audio=_never_downloads
            )


async def test_given_an_unrecognised_lookup_failure_when_reading_then_raises_video_unavailable_error() -> (
    None
):
    """Given yt-dlp failing in a way we have no specific handling for, when
    reading it, then it still surfaces as a video we could not read — never as
    an unhandled error."""
    extract_info = _extract_info_raising(RuntimeError("something deep inside the extractor"))

    with pytest.raises(VideoUnavailableError):
        await fetch_video(VIDEO_URL, extract_info=extract_info, download_audio=_never_downloads)


async def test_given_a_lookup_that_hangs_when_reading_then_raises_video_unavailable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Given a metadata lookup that never comes back, when reading it, then it
    is abandoned and reported as unavailable — the user is holding an open
    request the whole time, and there is no queue to hand the wait to."""
    monkeypatch.setattr(video_source, "_METADATA_TIMEOUT_SECONDS", 0.05)

    def extract_info(url: str) -> dict:
        threading.Event().wait(1.0)
        return _info_dict()

    with pytest.raises(VideoUnavailableError):
        await fetch_video(VIDEO_URL, extract_info=extract_info, download_audio=_never_downloads)


async def test_given_a_video_link_when_reading_then_the_lookup_runs_off_the_event_loop() -> None:
    """Given any video link, when reading it, then the blocking yt-dlp lookup
    happens on a worker thread.

    Not a detail: the route handler is async, so a lookup running inline would
    freeze the whole process — including the /health endpoint the compose
    healthcheck polls, which would flip the backend unhealthy while somebody
    is merely pasting a link.
    """
    lookup_threads: list[int] = []

    def extract_info(url: str) -> dict:
        lookup_threads.append(threading.get_ident())
        return _info_dict(subtitles={}, automatic_captions={})

    download_audio, _ = _download_audio_returning(AUDIO)

    await fetch_video(VIDEO_URL, extract_info=extract_info, download_audio=download_audio)

    assert lookup_threads and lookup_threads[0] != threading.get_ident()


async def test_given_a_video_longer_than_the_limit_when_reading_then_raises_video_too_long_error() -> (
    None
):
    """Given a three-hour livestream, when reading it, then it is refused
    before a single byte of captions or audio is fetched.

    Truncating it instead would silently produce a recipe from the first few
    minutes — plausible, and wrong.
    """
    extract_info, _ = _extract_info_returning(_info_dict(duration=3 * 60 * 60))
    transport, requests = _transport_serving({AUTO_CAPTION_URL: AUTO_CAPTIONS})

    with pytest.raises(VideoTooLongError):
        await fetch_video(
            VIDEO_URL,
            extract_info=extract_info,
            download_audio=_never_downloads,
            transport=transport,
        )

    assert requests == []


async def test_given_a_video_with_no_reported_duration_when_reading_then_it_is_still_read() -> None:
    """Given a video whose extractor reports no duration at all — several do —
    when reading it, then it is read anyway rather than refused on a length
    nobody knows."""
    extract_info, _ = _extract_info_returning(_info_dict(duration=None))
    transport, _ = _transport_serving({AUTO_CAPTION_URL: AUTO_CAPTIONS})

    material = await fetch_video(
        VIDEO_URL,
        extract_info=extract_info,
        download_audio=_never_downloads,
        transport=transport,
    )

    assert material.caption_transcript is not None


async def test_given_the_caption_download_fails_when_reading_then_the_audio_is_used_instead() -> (
    None
):
    """Given a caption url that no longer works — signed caption urls expire
    and answer 403 routinely — when reading it, then the audio path takes over
    instead of the whole submission failing."""
    extract_info, _ = _extract_info_returning(_info_dict())
    download_audio, downloaded = _download_audio_returning(AUDIO)

    def refusing(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="expired")

    material = await fetch_video(
        VIDEO_URL,
        extract_info=extract_info,
        download_audio=download_audio,
        transport=httpx.MockTransport(refusing),
    )

    assert material.caption_transcript is None
    assert material.audio == AUDIO
    assert downloaded == [VIDEO_URL]


async def test_given_the_caption_download_errors_out_when_reading_then_the_audio_is_used_instead() -> (
    None
):
    """Given the caption request failing at the network level, when reading it,
    then the audio path takes over — same reasoning as an expired url."""
    extract_info, _ = _extract_info_returning(_info_dict())
    download_audio, downloaded = _download_audio_returning(AUDIO)

    def failing(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    material = await fetch_video(
        VIDEO_URL,
        extract_info=extract_info,
        download_audio=download_audio,
        transport=httpx.MockTransport(failing),
    )

    assert material.caption_transcript is None
    assert material.audio == AUDIO
    assert downloaded == [VIDEO_URL]


async def test_given_a_video_with_no_text_and_no_audio_when_reading_then_raises_no_video_text_error() -> (
    None
):
    """Given a video with no captions, nothing usable written, and no audio to
    fall back on, when reading it, then there is nothing to make a recipe
    from and NoVideoTextError says so."""
    extract_info, _ = _extract_info_returning(
        _info_dict(description="Inscreva-se!", subtitles={}, automatic_captions={})
    )

    def no_audio(url: str) -> AudioClip | None:
        return None

    with pytest.raises(NoVideoTextError):
        await fetch_video(VIDEO_URL, extract_info=extract_info, download_audio=no_audio)


async def test_given_an_enormous_transcript_when_reading_then_it_is_truncated_and_the_description_survives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Given a caption track far longer than the model needs, when reading it,
    then the transcript is cut down while the description — the part that
    carries the quantities — is kept whole.

    Truncating rather than refusing on purpose: an over-long transcript is our
    problem to bound, not a reason to reject the user's video.
    """
    monkeypatch.setattr(video_source, "_MAX_TRANSCRIPT_CHARACTERS", 400)
    spoken = "\n".join(
        f"00:00:{second:02d}.000 --> 00:00:{second + 1:02d}.000\nmistura o ingrediente {second}"
        for second in range(0, 60)
    )
    extract_info, _ = _extract_info_returning(_info_dict())
    transport, _ = _transport_serving({AUTO_CAPTION_URL: f"WEBVTT\n\n{spoken}\n"})

    material = await fetch_video(
        VIDEO_URL,
        extract_info=extract_info,
        download_audio=_never_downloads,
        transport=transport,
    )

    assert material.caption_transcript is not None
    assert len(material.caption_transcript) <= 400 + len(video_source._TRUNCATION_MARKER)
    assert video_source._TRUNCATION_MARKER in material.caption_transcript
    assert "mistura o ingrediente 0" in material.caption_transcript
    assert material.description is not None
    assert "2 xícaras de farinha de trigo" in material.description


async def test_given_a_caption_fetch_when_it_is_sent_then_it_does_not_identify_itself_as_a_bot() -> (
    None
):
    """Given a caption download, when it is sent, then it carries a browser
    user agent — some anti-bot rules reject on the word "bot" alone, exactly
    as the scraper already works around."""
    extract_info, _ = _extract_info_returning(_info_dict())
    transport, requests = _transport_serving({AUTO_CAPTION_URL: AUTO_CAPTIONS})

    await fetch_video(
        VIDEO_URL,
        extract_info=extract_info,
        download_audio=_never_downloads,
        transport=transport,
    )

    user_agent = requests[0].headers["User-Agent"]
    assert "bot" not in user_agent.lower()
    assert "Mozilla/5.0" in user_agent


async def test_given_an_unreadable_video_when_reading_then_the_reason_is_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Given a video that cannot be read, when reading it, then the platform's
    own message is logged — on a server that log line is the only evidence of
    what actually happened."""
    extract_info = _extract_info_raising(DownloadError("ERROR: Private video."))

    with caplog.at_level("WARNING", logger="app.services.video_source"):
        with pytest.raises(VideoUnavailableError):
            await fetch_video(
                VIDEO_URL, extract_info=extract_info, download_audio=_never_downloads
            )

    assert VIDEO_URL in caplog.text
    assert "Private video" in caplog.text


def test_given_material_with_a_transcript_when_rendering_then_both_sources_are_labelled() -> None:
    """Given material with a written description and a narration transcript,
    when rendering it for the model, then each part is labelled and the
    description comes first — it is the part that carries the quantities, so
    it is also the part truncation must never reach."""
    material = video_source.VideoMaterial(
        title="Bolo de cenoura",
        uploader="Cozinha da Vovó",
        description=DESCRIPTION,
        caption_transcript="bate tudo no liquidificador",
        speech_source=SpeechSource.AUTOMATIC_CAPTIONS,
        audio=None,
    )

    rendered = render_material(material, speech="bate tudo no liquidificador")

    assert "Video title: Bolo de cenoura" in rendered
    assert "Channel: Cozinha da Vovó" in rendered
    assert rendered.index("Description:") < rendered.index("3 cenouras médias")
    assert rendered.index("3 cenouras médias") < rendered.index("bate tudo no liquidificador")
    assert str(SpeechSource.AUTOMATIC_CAPTIONS) in rendered


def test_given_material_when_rendering_then_the_videos_duration_is_left_out() -> None:
    """Given any material, when rendering it, then the video's length is not
    in it.

    A "Duration: 6 minutes" line reads as a recipe timing to a model, and a
    video's length is not its cooking time. The duration is used to refuse
    over-long videos and then deliberately dropped.
    """
    material = video_source.VideoMaterial(
        title="Bolo de cenoura",
        uploader="Cozinha da Vovó",
        description=DESCRIPTION,
        caption_transcript="bate tudo",
        speech_source=SpeechSource.AUTOMATIC_CAPTIONS,
        audio=None,
    )

    rendered = render_material(material, speech="bate tudo")

    assert "Duration" not in rendered
    assert "minutes" not in rendered


def test_given_material_transcribed_from_audio_when_rendering_then_the_label_says_so() -> None:
    """Given narration that came from speech recognition rather than a
    published caption track, when rendering it, then the label says which —
    telling the model how much to trust the text is free, and changes how it
    treats a mis-heard ingredient."""
    material = video_source.VideoMaterial(
        title="Bolo de cenoura",
        uploader="Cozinha da Vovó",
        description=None,
        caption_transcript=None,
        speech_source=None,
        audio=AUDIO,
    )

    rendered = render_material(
        material,
        speech="bate tudo no liquidificador",
        speech_source=SpeechSource.AUDIO_TRANSCRIPTION,
    )

    assert str(SpeechSource.AUDIO_TRANSCRIPTION) in rendered
    assert str(SpeechSource.AUTOMATIC_CAPTIONS) not in rendered


def test_given_the_metadata_lookup_when_it_is_configured_then_a_playlist_is_never_enumerated() -> (
    None
):
    """Given the options the metadata lookup runs with, when inspecting them,
    then they ask for a flat lookup with no playlist items at all.

    Measured against a real YouTube channel: 0.5s with both of these, 82s with
    only the flat lookup, and past the 30-second timeout with neither — because
    yt-dlp pages through every video on the channel before answering. Without
    them, "envie o link de um vídeo específico" is a message the user would
    never actually get: a channel link would time out into the generic
    unavailable message instead.
    """
    options = video_source._metadata_options()

    assert options["extract_flat"] == "in_playlist"
    assert options["playlist_items"] == "0"
    assert options["skip_download"] is True


def test_given_no_cookies_file_is_configured_when_looking_up_then_yt_dlp_stays_anonymous() -> None:
    """Given no cookies file configured — the default — when building the
    lookup options, then no cookie jar is handed to yt-dlp.

    A cookies file is a live credential to a personal account, so it is only
    ever used when explicitly set.
    """
    assert "cookiefile" not in video_source._metadata_options()


def test_given_a_cookies_file_is_configured_when_looking_up_then_it_is_handed_to_yt_dlp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Given a cookies file is configured, when building the lookup options,
    then it is passed through — the escape hatch for a platform that refuses
    anonymous requests from the server."""
    settings = video_source.get_settings()
    monkeypatch.setattr(settings, "video_cookies_file", "/run/secrets/cookies.txt")

    assert video_source._metadata_options()["cookiefile"] == "/run/secrets/cookies.txt"


def test_given_the_module_when_inspecting_its_limits_then_the_audio_cap_fits_the_providers() -> None:
    """Given the audio size cap, when checking it, then it sits under the 25 MB
    the transcription endpoint accepts — a clip we refuse ourselves gives a
    Portuguese explanation, where one the provider refuses gives a 502."""
    assert video_source.MAX_AUDIO_BYTES < 25 * 1024 * 1024


async def test_given_asyncio_is_used_when_reading_a_video_then_nothing_blocks_the_loop() -> None:
    """Given a read in progress, when other work is scheduled, then it still
    runs — the guarantee the worker-thread hand-off exists to provide."""
    ticks = 0

    async def tick() -> None:
        nonlocal ticks
        for _ in range(5):
            await asyncio.sleep(0.01)
            ticks += 1

    def slow_extract_info(url: str) -> dict:
        threading.Event().wait(0.1)
        return _info_dict(subtitles={}, automatic_captions={})

    download_audio, _ = _download_audio_returning(AUDIO)

    await asyncio.gather(
        fetch_video(VIDEO_URL, extract_info=slow_extract_info, download_audio=download_audio),
        tick(),
    )

    assert ticks == 5
