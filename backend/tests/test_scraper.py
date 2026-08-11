"""Specifications for the recipe page scraper.

Fetches a page and extracts its main readable text, discarding navigation,
ads, and other boilerplate — the extracted text is what gets sent to the AI
extractor in a later layer.
"""

from pathlib import Path

import httpx
import pytest

from app.services.scraper import (
    NoExtractableContentError,
    UnreachableUrlError,
    fetch_and_extract_text,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
RECIPE_URL = "https://example.com/receita/bolo-de-cenoura"


def _transport_returning(html: str, status_code: int = 200) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text=html)

    return httpx.MockTransport(handler)


def _failing_transport(exception: httpx.HTTPError) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exception

    return httpx.MockTransport(handler)


async def test_given_a_reachable_recipe_page_when_extracting_then_returns_main_content() -> None:
    """Given a page with a recipe article surrounded by nav/ads/footer, when
    fetched and extracted, then the returned text has the recipe content and
    excludes the surrounding boilerplate."""
    html = (FIXTURES_DIR / "recipe_page.html").read_text(encoding="utf-8")
    transport = _transport_returning(html)

    text = await fetch_and_extract_text(RECIPE_URL, transport=transport)

    assert "Bolo de Cenoura Fácil" in text
    assert "cenouras médias raladas" in text
    assert "180°C" in text
    assert "Publicidade" not in text
    assert "Política de Privacidade" not in text
    assert "Você também pode gostar" not in text


async def test_given_the_url_returns_an_error_status_when_fetching_then_raises_unreachable_url_error() -> None:
    """Given the source URL responds with an HTTP error status, when
    fetching, then an UnreachableUrlError is raised."""
    transport = _transport_returning("not found", status_code=404)

    with pytest.raises(UnreachableUrlError):
        await fetch_and_extract_text(RECIPE_URL, transport=transport)


async def test_given_a_network_failure_when_fetching_then_raises_unreachable_url_error() -> None:
    """Given the connection to the source URL fails outright, when fetching,
    then an UnreachableUrlError is raised."""
    transport = _failing_transport(httpx.ConnectError("connection refused"))

    with pytest.raises(UnreachableUrlError):
        await fetch_and_extract_text(RECIPE_URL, transport=transport)


async def test_given_a_page_with_no_meaningful_content_when_extracting_then_raises_no_extractable_content_error() -> None:
    """Given the fetched page has no substantive text (just nav/footer),
    when extracting, then a NoExtractableContentError is raised."""
    html = (FIXTURES_DIR / "empty_page.html").read_text(encoding="utf-8")
    transport = _transport_returning(html)

    with pytest.raises(NoExtractableContentError):
        await fetch_and_extract_text(RECIPE_URL, transport=transport)
