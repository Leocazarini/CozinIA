"""Fetches a web page and extracts its recipe text."""

import logging

import httpx
import trafilatura

from app.services.recipe_json_ld import extract_recipe_text as extract_json_ld_recipe_text

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT_SECONDS = 15.0

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


async def fetch_and_extract_text(
    url: str, *, transport: httpx.AsyncBaseTransport | None = None
) -> str:
    """Fetch `url` and return its recipe text.

    Prefers a schema.org/Recipe block from the page's JSON-LD, when present
    (see recipe_json_ld.py) — it's already structured and free of
    boilerplate, which makes it far more reliable than reconstructing the
    same fields from prose. Falls back to the main readable text (stripped
    of navigation, ads, and other boilerplate) when no such block is found.

    Raises UnreachableUrlError if the page cannot be fetched, and
    NoExtractableContentError if no meaningful text could be extracted from it
    either way.

    `transport` is exposed so tests can inject an httpx.MockTransport
    instead of hitting the real network.
    """
    html = await _fetch_html(url, transport=transport)

    json_ld_text = extract_json_ld_recipe_text(html)
    if json_ld_text is not None:
        return json_ld_text

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
            status = getattr(getattr(error, "response", None), "status_code", "unknown")
            logger.warning("Could not fetch %s (status=%s): %s", url, status, error)
            raise UnreachableUrlError(f"Could not fetch {url}: {error}") from error
    return response.text
