"""Reads a video link into the material a recipe can be reconstructed from.

This is the video flow's counterpart to `scraper.fetch_and_extract_text`:
where that one turns a page into text, this one turns a video into the title,
the description its author wrote, and a transcript of what is narrated — the
two places a video's recipe actually lives, since a Reel typically lists the
quantities in its caption and explains the method out loud.

The narration is read the cheap way first, mirroring how the scraper prefers
JSON-LD over readable text: a caption track the platform already publishes
costs one plain HTTP request, while transcribing audio costs a download and a
model call. Platforms that publish no captions — which is most of Instagram
and TikTok, exactly where recipes are spoken rather than written — fall
through to the audio, which is downloaded to a temporary directory and never
stored, the same way uploaded photos are never stored.

Two of the three networks here are yt-dlp's own (metadata and media, both
through urllib, both invisible to httpx) so they are injected as callables;
the caption download is ours over httpx and uses the same `transport` seam the
scraper does.
"""

import asyncio
import ipaddress
import logging
import socket
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from app.core.config import get_settings
from app.services.video_captions import transcript_from_vtt

logger = logging.getLogger(__name__)

MAX_VIDEO_DURATION_MINUTES = 30
MAX_AUDIO_BYTES = 24 * 1024 * 1024

# Below this there is not enough recipe-bearing text for an attempt to be
# worth making — the same floor scraper.py applies to a page. Public because
# the video pass applies it a second time, once speech recognition has had its
# turn at a video whose captions were missing.
MINIMUM_VIDEO_TEXT_LENGTH = 100

_MAX_VIDEO_DURATION_SECONDS = MAX_VIDEO_DURATION_MINUTES * 60
_MAX_DESCRIPTION_CHARACTERS = 5_000
_MAX_TRANSCRIPT_CHARACTERS = 35_000
# The raw caption file, before de-duplication collapses it. A 30-minute
# automatic track is around 500 KB of rolling-window repetition, so this only
# catches a broken or hostile file.
_MAX_CAPTION_CHARACTERS = 1_000_000
_TRUNCATION_MARKER = "\n[... transcript truncated ...]"

_SOCKET_TIMEOUT_SECONDS = 15
_METADATA_TIMEOUT_SECONDS = 30.0
_AUDIO_DOWNLOAD_TIMEOUT_SECONDS = 180.0
_CAPTION_TIMEOUT_SECONDS = 15.0

# Same reasoning as scraper.py's: a generic browser UA rather than one that
# self-identifies as a bot, because some anti-bot rules block on that word
# alone regardless of actual behaviour.
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

_CAPTION_FORMAT = "vtt"
_PREFERRED_LANGUAGES = ("pt", "pt-BR", "pt-PT", "en", "en-US")

# yt-dlp reports "this video is private" and "the platform is refusing our
# server" as the same exception class, distinguishable only by message text.
# Matching on text is fragile, which is why VideoAccessBlockedError subclasses
# VideoUnavailableError: when one of these markers stops matching, the user
# gets the generic (still truthful) message instead of an unhandled error.
_BLOCKED_MARKERS = (
    "sign in to confirm",
    "confirm you're not a bot",
    "login required",
    "requires authentication",
    "rate-limit",
    "rate limit",
    "http error 429",
)

# mp3 at 16 kHz mono, which the transcription endpoint accepts (see
# TRANSCRIBABLE_AUDIO_FORMATS) and which keeps the file small: measured at
# ~4 MB for 9 minutes, so half an hour — the duration cap — lands around
# 13 MB, comfortably under MAX_AUDIO_BYTES. flac transcribes slightly better
# but runs 20 MB for those same 9 minutes, which would blow the cap on any
# long video.
_AUDIO_FORMAT = "mp3"
_AUDIO_BITRATE = "64k"
# Smallest audio-only stream that is still speech-legible, falling back to
# whatever exists — a combined stream on platforms that offer nothing else.
# Whisper gains nothing from a higher bitrate, and every byte here is a byte
# uploaded again to the transcription endpoint.
_AUDIO_FORMAT_SELECTOR = "worstaudio[abr>=32]/bestaudio/best"


class SpeechSource(StrEnum):
    """Where a video's narration came from, and how much it can be trusted.

    The value is the label handed to the model: knowing whether a line was
    written by a person or guessed by speech recognition is what tells it
    whether an odd-looking ingredient is a mis-hearing to repair.
    """

    UPLOADER_SUBTITLES = "subtitles written by the uploader"
    AUTOMATIC_CAPTIONS = "automatic captions, may contain transcription errors"
    AUDIO_TRANSCRIPTION = "speech recognition of the audio, may contain transcription errors"


@dataclass(frozen=True)
class AudioClip:
    """A video's audio, in memory, on its way to the transcription endpoint."""

    data: bytes
    audio_format: str


@dataclass(frozen=True)
class VideoMaterial:
    """Everything read off a video link, before any of it reaches a model.

    Either `caption_transcript` or `audio` carries the narration: the caption
    track when the platform published one, the audio when it didn't.
    """

    title: str | None
    uploader: str | None
    description: str | None
    caption_transcript: str | None
    speech_source: SpeechSource | None
    audio: AudioClip | None


class VideoSourceError(Exception):
    """Base exception for failures reading a video link."""


class UnsupportedVideoUrlError(VideoSourceError):
    """Raised when the link is not one we will fetch as a video — a scheme we
    never follow, an address on a private network, or a page with no video in
    it at all."""


class NotASingleVideoError(VideoSourceError):
    """Raised when the link points at a channel, profile or playlist rather
    than one video."""


class VideoUnavailableError(VideoSourceError):
    """Raised when the video cannot be read: private, deleted, geo-blocked, or
    the lookup failed or timed out."""


class VideoAccessBlockedError(VideoUnavailableError):
    """Raised when the platform is refusing our server specifically — an
    anti-bot challenge or a rate limit, rather than anything wrong with the
    link the user pasted."""


class VideoTooLongError(VideoSourceError):
    """Raised when the video runs longer than we are willing to read."""


class AudioTooLargeError(VideoTooLongError):
    """Raised when a video's audio is too large to transcribe. Defensive: the
    duration limit plus a downmixed stream should keep clips far below the cap,
    so this subclasses VideoTooLongError to reuse its explanation."""


class NoVideoTextError(VideoSourceError):
    """Raised when a video yields no recipe-bearing text at all — no captions,
    no audio, and nothing usable written in its description."""


def _build_options(**overrides: object) -> dict:
    settings = get_settings()
    options: dict = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": _SOCKET_TIMEOUT_SECONDS,
        # No retries: a failing extractor would multiply the wait by the retry
        # count, and there is no queue to absorb that — the user is holding an
        # open HTTP request for the whole thing.
        "retries": 0,
        "extractor_retries": 0,
        **overrides,
    }
    if settings.video_cookies_file:
        options["cookiefile"] = settings.video_cookies_file
    return options


def _metadata_options() -> dict:
    """Options for the metadata lookup.

    `extract_flat` plus `playlist_items="0"` are what make a channel or
    playlist link come back immediately, as a playlist with no entries, so the
    "send one video" refusal is reachable at all. Measured against a real
    YouTube channel: 0.5s with both, 82s with only the flat lookup, and past
    the 30-second timeout with neither, because yt-dlp pages through every
    video on the channel before answering. Neither affects a single video.

    They belong here rather than in the shared options because asking the
    audio download for zero playlist items is asking it to download nothing.
    """
    return _build_options(skip_download=True, extract_flat="in_playlist", playlist_items="0")


def _extract_info(url: str) -> dict | None:
    """Blocking: yt-dlp is synchronous urllib. Always called through
    asyncio.to_thread — see fetch_video."""
    with YoutubeDL(_metadata_options()) as downloader:
        return downloader.extract_info(url, download=False)


def _download_audio(url: str) -> AudioClip | None:
    """Blocking, and always called through asyncio.to_thread.

    Downloads into a temporary directory that goes away with the function: the
    audio is a means of reading the recipe, never something the app keeps.
    """
    with tempfile.TemporaryDirectory(prefix="cozinia-audio-") as directory:
        options = _build_options(
            format=_AUDIO_FORMAT_SELECTOR,
            outtmpl=str(Path(directory) / "audio.%(ext)s"),
            postprocessors=[
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": _AUDIO_FORMAT,
                }
            ],
            # 16 kHz mono is all speech recognition uses, and it is what keeps
            # half an hour of narration down to a few megabytes.
            postprocessor_args={
                "extractaudio": ["-ar", "16000", "-ac", "1", "-b:a", _AUDIO_BITRATE]
            },
        )
        with YoutubeDL(options) as downloader:
            downloader.download([url])

        downloaded = sorted(Path(directory).glob("audio.*"))
        if not downloaded:
            return None

        clip = downloaded[0]
        size = clip.stat().st_size
        if size > MAX_AUDIO_BYTES:
            raise AudioTooLargeError(f"Audio for {url} is {size} bytes, over the cap")
        return AudioClip(data=clip.read_bytes(), audio_format=clip.suffix.lstrip("."))


async def fetch_video(
    url: str,
    *,
    extract_info: Callable[[str], dict | None] | None = None,
    download_audio: Callable[[str], AudioClip | None] | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> VideoMaterial:
    """Read the video at `url` and return the material to build a recipe from.

    Raises UnsupportedVideoUrlError, NotASingleVideoError,
    VideoUnavailableError, VideoAccessBlockedError, VideoTooLongError and
    NoVideoTextError. The API layer is responsible for turning those into
    user-facing responses.

    `extract_info` and `download_audio` are exposed because yt-dlp networks
    through urllib, which no httpx transport can intercept; `transport` covers
    the caption download, which is ours. Tests inject all three.
    """
    lookup = extract_info if extract_info is not None else _extract_info
    fetch_audio = download_audio if download_audio is not None else _download_audio

    await asyncio.to_thread(_assert_fetchable, url)
    info = await _look_up(url, lookup)
    _assert_single_video(info)
    _assert_within_duration_limit(url, info)

    description = _truncate(_text_or_none(info.get("description")), _MAX_DESCRIPTION_CHARACTERS)
    speech_source, transcript = await _read_captions(info, transport=transport)

    audio = None
    if transcript is None:
        audio = await _download(url, fetch_audio)

    if audio is None and len(f"{description or ''}{transcript or ''}") < MINIMUM_VIDEO_TEXT_LENGTH:
        # Measured on the recipe-bearing text alone, never on the rendered
        # material: the labels by themselves are longer than this floor, so
        # checking the assembled string would make it unreachable.
        raise NoVideoTextError(f"No captions, audio or usable description for {url}")

    return VideoMaterial(
        title=_text_or_none(info.get("title")),
        uploader=_text_or_none(info.get("uploader") or info.get("channel")),
        description=description,
        caption_transcript=transcript,
        speech_source=speech_source,
        audio=audio,
    )


def render_material(
    material: VideoMaterial,
    *,
    speech: str | None,
    speech_source: SpeechSource | None = None,
) -> str:
    """Render `material` as the labelled plain text a model reads.

    The description comes before the narration: it is the higher-signal half
    (quantities are usually written, not spoken), and putting it first means
    truncation eats the transcript rather than the ingredient list. There is
    deliberately no line for the video's length — "Duration: 6 minutes" reads
    as a recipe timing, and a video's length is not its cooking time.
    """
    lines: list[str] = []

    if material.title:
        lines.append(f"Video title: {material.title}")
    if material.uploader:
        lines.append(f"Channel: {material.uploader}")
    if material.description:
        lines.append("Description:")
        lines.append(material.description)
    if speech:
        source = speech_source or material.speech_source or SpeechSource.AUTOMATIC_CAPTIONS
        lines.append(f"Spoken narration ({source}):")
        lines.append(speech)

    return "\n".join(lines)


async def _look_up(url: str, extract_info: Callable[[str], dict | None]) -> dict:
    """Run the blocking metadata lookup on a worker thread.

    The socket timeout inside yt-dlp is what actually bounds the work, because
    asyncio.to_thread cannot be cancelled: the wait_for below stops us waiting
    but the thread runs on. That leaked thread is acceptable here precisely
    because socket_timeout caps it — bounding it properly would need the
    background queue this app deliberately does not have.
    """
    try:
        info = await asyncio.wait_for(
            asyncio.to_thread(extract_info, url), _METADATA_TIMEOUT_SECONDS
        )
    except TimeoutError as error:
        logger.warning("Timed out reading metadata for %s", url)
        raise VideoUnavailableError(f"Timed out reading {url}") from error
    except DownloadError as error:
        raise _lookup_failure(url, error) from error
    except Exception as error:  # noqa: BLE001 - a boundary: yt-dlp raises freely
        logger.warning("Could not read %s: %s", url, error)
        raise VideoUnavailableError(f"Could not read {url}: {error}") from error

    if not info:
        logger.warning("No metadata returned for %s", url)
        raise VideoUnavailableError(f"No metadata returned for {url}")
    return info


def _lookup_failure(url: str, error: DownloadError) -> VideoUnavailableError:
    """Classify a yt-dlp failure, logging the platform's own words — on a
    server that log line is the only evidence of what really happened."""
    message = str(error)
    logger.warning("Could not read %s: %s", url, message)

    lowered = message.lower()
    if any(marker in lowered for marker in _BLOCKED_MARKERS):
        return VideoAccessBlockedError(f"The platform is refusing our requests: {message}")
    return VideoUnavailableError(f"Could not read {url}: {message}")


def _assert_fetchable(url: str) -> None:
    """Refuse links we will not hand to a media downloader, before any lookup.

    This is the one place the app passes a user-supplied url to a library that
    fetches it server-side, so a scheme we never follow and any address on a
    private network are rejected here. Resolving again inside yt-dlp means this
    is not proof against a host that changes its answer between the two
    lookups; it is the check that keeps an ordinary pasted link from reaching
    localhost or a metadata endpoint.
    """
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise UnsupportedVideoUrlError(f"Not a fetchable video url: {url}")

    try:
        resolved = socket.getaddrinfo(parts.hostname, None)
    except OSError as error:
        logger.warning("Could not resolve %s: %s", parts.hostname, error)
        raise VideoUnavailableError(f"Could not resolve {parts.hostname}") from error

    # The address is the first field of the sockaddr tuple; for IPv6 the last
    # field is the scope id, which is an integer and not an address at all.
    for sockaddr in (entry[-1] for entry in resolved):
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise UnsupportedVideoUrlError(f"Refusing to fetch a private address: {url}")


def _assert_single_video(info: dict) -> None:
    """Refuse anything that isn't one video, before reading anything from it."""
    if info.get("_type") not in (None, "video"):
        raise NotASingleVideoError("The link is a channel, profile or playlist, not a video")

    # yt-dlp's generic extractor matches almost any url and goes looking for
    # media rather than refusing, so "this isn't a video" is a conclusion we
    # reach here, after the fact, instead of something it tells us.
    if info.get("extractor") == "generic" and not info.get("formats"):
        raise UnsupportedVideoUrlError("No video found at that link")


def _assert_within_duration_limit(url: str, info: dict) -> None:
    """Refuse over-long videos before a byte of captions or audio is fetched.

    Truncating instead would silently build a recipe out of the first few
    minutes of a three-hour stream — plausible, and wrong. A missing duration
    (several extractors report none) is not treated as a failure: the character
    caps downstream still bound the work.
    """
    duration = info.get("duration")
    if isinstance(duration, (int, float)) and duration > _MAX_VIDEO_DURATION_SECONDS:
        raise VideoTooLongError(f"{url} runs {duration:.0f}s, over the limit")


async def _read_captions(
    info: dict, *, transport: httpx.AsyncBaseTransport | None
) -> tuple[SpeechSource | None, str | None]:
    """Fetch and parse the best caption track, or return (None, None).

    Every failure here is non-fatal: signed caption urls expire and answer 403
    routinely, and a video whose narration has to come from its audio instead
    is a normal outcome, not a broken submission.
    """
    chosen = _choose_caption_track(info)
    if chosen is None:
        return None, None

    source, caption_url = chosen
    try:
        async with httpx.AsyncClient(
            timeout=_CAPTION_TIMEOUT_SECONDS,
            headers={"User-Agent": _USER_AGENT},
            transport=transport,
        ) as client:
            response = await client.get(caption_url, follow_redirects=True)
            response.raise_for_status()
    except httpx.HTTPError as error:
        logger.warning("Could not download the caption track: %s", error)
        return None, None

    transcript = transcript_from_vtt(response.text[:_MAX_CAPTION_CHARACTERS])
    if transcript is None:
        return None, None
    return source, _truncate(transcript, _MAX_TRANSCRIPT_CHARACTERS)


def _choose_caption_track(info: dict) -> tuple[SpeechSource, str] | None:
    """Pick the caption track most worth reading, or None if there is none.

    Subtitles written by the uploader beat automatic captions, which are
    punctuated by nobody and mis-hear ingredient names. Within each, the
    video's own language comes first: YouTube lists one automatic-caption entry
    per translation target, so asking for "pt" on an English video returns a
    machine translation of a machine transcription.
    """
    for key, source in (
        ("subtitles", SpeechSource.UPLOADER_SUBTITLES),
        ("automatic_captions", SpeechSource.AUTOMATIC_CAPTIONS),
    ):
        tracks = info.get(key) or {}
        for language in _language_preference(info, tracks):
            for entry in tracks.get(language) or []:
                if entry.get("ext") == _CAPTION_FORMAT and entry.get("url"):
                    return source, str(entry["url"])
    return None


def _language_preference(info: dict, tracks: dict) -> list[str]:
    """The languages to try, best first: the video's own, then ours, then
    whatever exists (sorted, so the choice is deterministic)."""
    spoken = info.get("language")
    preferred = [f"{spoken}-orig", spoken] if spoken else []
    preferred += list(_PREFERRED_LANGUAGES)

    ordered = [language for language in preferred if language in tracks]
    ordered += sorted(language for language in tracks if language not in ordered)
    return ordered


async def _download(
    url: str, download_audio: Callable[[str], AudioClip | None]
) -> AudioClip | None:
    """Run the blocking audio download on a worker thread. Same cancellation
    caveat as the metadata lookup — see _look_up."""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(download_audio, url), _AUDIO_DOWNLOAD_TIMEOUT_SECONDS
        )
    except TimeoutError as error:
        logger.warning("Timed out downloading the audio of %s", url)
        raise VideoUnavailableError(f"Timed out downloading the audio of {url}") from error
    except (VideoSourceError, AssertionError):
        raise
    except DownloadError as error:
        raise _lookup_failure(url, error) from error
    except Exception as error:  # noqa: BLE001 - a boundary: yt-dlp raises freely
        logger.warning("Could not download the audio of %s: %s", url, error)
        return None


def _text_or_none(value: object) -> str | None:
    """Normalise a metadata field to non-empty text, or None."""
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _truncate(text: str | None, limit: int) -> str | None:
    """Cut `text` down to `limit`, keeping the head.

    Head and not tail: a recipe video states its ingredients up front and
    spends its last minute on the outro. Truncating never fails the request —
    an over-long transcript is ours to bound, not a reason to refuse the
    user's video — but it is logged, because it is the signal that the caps
    need revisiting.
    """
    if text is None or len(text) <= limit:
        return text
    logger.warning("Truncating %d characters of video text to %d", len(text), limit)
    return text[:limit] + _TRUNCATION_MARKER
