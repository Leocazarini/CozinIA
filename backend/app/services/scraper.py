"""Fetches a web page and extracts its main readable text content."""

import httpx
import trafilatura

_REQUEST_TIMEOUT_SECONDS = 15.0
_USER_AGENT = "Mozilla/5.0 (compatible; CoziniaBot/1.0)"

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


async def fetch_and_extract_text(
    url: str, *, transport: httpx.AsyncBaseTransport | None = None
) -> str:
    """Fetch `url` and return its main readable text, stripped of
    navigation, ads, and other boilerplate.

    Raises UnreachableUrlError if the page cannot be fetched, and
    NoExtractableContentError if no meaningful text could be extracted from it.

    `transport` is exposed so tests can inject an httpx.MockTransport
    instead of hitting the real network.
    """
    html = await _fetch_html(url, transport=transport)
    text = trafilatura.extract(html, include_comments=False, include_tables=True)
    text = text.strip() if text else ""
    if len(text) < _MINIMUM_EXTRACTED_TEXT_LENGTH:
        raise NoExtractableContentError(f"No extractable content found at {url}")
    return text


async def _fetch_html(url: str, *, transport: httpx.AsyncBaseTransport | None = None) -> str:
    async with httpx.AsyncClient(
        timeout=_REQUEST_TIMEOUT_SECONDS,
        headers={"User-Agent": _USER_AGENT},
        transport=transport,
    ) as client:
        try:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise UnreachableUrlError(f"Could not fetch {url}: {error}") from error
    return response.text
