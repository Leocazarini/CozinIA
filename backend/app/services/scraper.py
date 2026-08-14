"""Fetches a web page and extracts its recipe text."""

import ipaddress
import logging
import socket
from urllib.parse import urljoin, urlsplit

import httpx
import trafilatura

from app.services.recipe_json_ld import extract_recipe_text as extract_json_ld_recipe_text

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT_SECONDS = 15.0

# The response body is read with a hard cap so a link to a huge (or endless)
# file can't exhaust memory. Recipe pages are a few hundred KB at most.
_MAX_RESPONSE_BYTES = 5 * 1024 * 1024

# Redirects are followed by hand (not by httpx) so every hop can be
# re-validated against the private-address guard — otherwise a public URL could
# 302 to http://169.254.169.254 and slip past the check. This caps the chain.
_MAX_REDIRECTS = 5

# The extracted text handed to the AI is capped, mirroring the video door
# (see app/services/video_source.py): it bounds both the model cost and how
# much attacker-controlled text can try to steer the extraction prompt.
_MAX_EXTRACTED_TEXT_CHARS = 50_000

# A generic browser UA rather than one that self-identifies as a bot
# ("CozinIABot/1.0" et al.) — some anti-bot/WAF rules block on the word
# "bot" alone, regardless of actual origin or behavior.
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

# trafilatura falls back to whatever text it can find (e.g. a single nav
# link) when a page has no clear main content, instead of returning nothing.
# A real recipe's ingredients and steps are always well above this length,
# so a short result is treated as "nothing meaningful was extracted".
_MINIMUM_EXTRACTED_TEXT_LENGTH = 100


class ScraperError(Exception):
    """Base exception for recipe page scraping failures."""


class UnreachableUrlError(ScraperError):
    """Raised when the source URL could not be fetched."""


class NoExtractableContentError(ScraperError):
    """Raised when the fetched page has no meaningful text to extract."""


def _assert_public_url(url: str) -> None:
    """Refuse a URL that points at a private, internal or non-HTTP address.

    The scraper hands a user-supplied URL to an HTTP client that fetches it
    server-side, so without this an attacker could aim it at cloud metadata
    (169.254.169.254), the database (db:5432), or anything else only the server
    can reach — a classic SSRF. Every host is resolved and every resolved
    address checked; this runs before each request, including on each redirect
    hop, since a public host can redirect to a private one.

    This is the same guard app/services/video_source.py applies on the video
    door — the two are the only places the app fetches a URL the user chose.
    """
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise UnreachableUrlError(f"Refusing to fetch a non-http(s) url: {url}")

    try:
        resolved = socket.getaddrinfo(parts.hostname, None)
    except OSError as error:
        logger.warning("Could not resolve %s: %s", parts.hostname, error)
        raise UnreachableUrlError(f"Could not resolve {parts.hostname}") from error

    # The address is the first field of the sockaddr tuple; for IPv6 the last
    # field is the scope id, which is an integer and not an address at all.
    for sockaddr in (entry[-1] for entry in resolved):
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            logger.warning("Refusing to fetch a private address: %s (%s)", url, ip)
            raise UnreachableUrlError(f"Refusing to fetch a private address: {url}")


async def fetch_and_extract_text(
    url: str, *, transport: httpx.AsyncBaseTransport | None = None
) -> str:
    """Fetch `url` and return its recipe text.

    Prefers a schema.org/Recipe block from the page's JSON-LD, when present
    (see recipe_json_ld.py) — it's already structured and free of
    boilerplate, which makes it far more reliable than reconstructing the
    same fields from prose. Falls back to the main readable text (stripped
    of navigation, ads, and other boilerplate) when no such block is found.

    Raises UnreachableUrlError if the page cannot be fetched (including when it
    resolves to a private/internal address), and NoExtractableContentError if
    no meaningful text could be extracted from it either way.

    `transport` is exposed so tests can inject an httpx.MockTransport
    instead of hitting the real network.
    """
    html = await _fetch_html(url, transport=transport)

    json_ld_text = extract_json_ld_recipe_text(html)
    if json_ld_text is not None:
        return json_ld_text[:_MAX_EXTRACTED_TEXT_CHARS]

    text = trafilatura.extract(html, include_comments=False, include_tables=True)
    text = text.strip() if text else ""
    if len(text) < _MINIMUM_EXTRACTED_TEXT_LENGTH:
        raise NoExtractableContentError(f"No extractable content found at {url}")
    return text[:_MAX_EXTRACTED_TEXT_CHARS]


async def _fetch_html(url: str, *, transport: httpx.AsyncBaseTransport | None = None) -> str:
    async with httpx.AsyncClient(
        timeout=_REQUEST_TIMEOUT_SECONDS,
        headers={"User-Agent": _USER_AGENT},
        transport=transport,
        # Redirects are followed by hand below so each hop is re-validated.
        follow_redirects=False,
    ) as client:
        current_url = url
        for _ in range(_MAX_REDIRECTS + 1):
            _assert_public_url(current_url)
            try:
                response = await client.get(current_url)
            except httpx.HTTPError as error:
                logger.warning("Could not fetch %s: %s", current_url, error)
                raise UnreachableUrlError(f"Could not fetch {current_url}: {error}") from error

            if response.is_redirect and response.headers.get("location"):
                current_url = urljoin(current_url, response.headers["location"])
                continue

            try:
                response.raise_for_status()
            except httpx.HTTPError as error:
                status = getattr(getattr(error, "response", None), "status_code", "unknown")
                logger.warning("Could not fetch %s (status=%s): %s", current_url, status, error)
                raise UnreachableUrlError(f"Could not fetch {current_url}: {error}") from error

            return _read_capped(response, current_url)

        logger.warning("Too many redirects starting at %s", url)
        raise UnreachableUrlError(f"Too many redirects for {url}")


def _read_capped(response: httpx.Response, url: str) -> str:
    """Return the response body as text, refusing anything over the size cap.

    httpx has already buffered the body here; the guard is against a server
    that advertises or streams far more than a recipe page ever would, so an
    oversized response is rejected rather than decoded and processed.
    """
    if len(response.content) > _MAX_RESPONSE_BYTES:
        logger.warning("Response from %s exceeds %d bytes", url, _MAX_RESPONSE_BYTES)
        raise UnreachableUrlError(f"Response too large from {url}")
    return response.text
