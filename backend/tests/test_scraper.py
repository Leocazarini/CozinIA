"""Specifications for the recipe page scraper.

Fetches a page and extracts its recipe text: a schema.org/Recipe JSON-LD
block when the page has one (clean and already structured — see
recipe_json_ld.py), otherwise falling back to the main readable text with
navigation/ads/boilerplate stripped out. Either way, this is the text that
gets sent to the AI extractor in a later layer.
"""

import json
import logging
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


async def test_given_the_url_returns_an_error_status_when_fetching_then_raises_unreachable_url_error() -> (
    None
):
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


async def test_given_a_page_with_no_meaningful_content_when_extracting_then_raises_no_extractable_content_error() -> (
    None
):
    """Given the fetched page has no substantive text (just nav/footer),
    when extracting, then a NoExtractableContentError is raised."""
    html = (FIXTURES_DIR / "empty_page.html").read_text(encoding="utf-8")
    transport = _transport_returning(html)

    with pytest.raises(NoExtractableContentError):
        await fetch_and_extract_text(RECIPE_URL, transport=transport)


async def test_given_a_page_with_recipe_json_ld_when_extracting_then_it_is_preferred_over_readable_text() -> (
    None
):
    """Given a page whose visible article text is a vague teaser but whose
    schema.org/Recipe JSON-LD has the full ingredient list (a real pattern:
    ingredients rendered by a JS widget outside the readable article), when
    extracting, then the JSON-LD's ingredients are returned — proving the
    structured data wins over the (incomplete) readable text."""
    html = """
    <html><head>
      <script type="application/ld+json">{
        "@type": "Recipe",
        "name": "Pudim de Leite Condensado",
        "recipeIngredient": ["1 lata de leite condensado", "3 ovos", "200g de açúcar"],
        "recipeInstructions": ["Bata tudo no liquidificador.", "Asse por 60 minutos."]
      }</script>
    </head><body>
      <article><p>Uma sobremesa clássica que todo mundo ama.</p></article>
    </body></html>
    """
    transport = _transport_returning(html)

    text = await fetch_and_extract_text(RECIPE_URL, transport=transport)

    assert "1 lata de leite condensado" in text
    assert "3 ovos" in text


async def test_given_a_page_with_no_usable_json_ld_when_extracting_then_falls_back_to_readable_text() -> (
    None
):
    """Given a page whose only ld+json blocks aren't a usable Recipe (e.g.
    just Organization/WebSite metadata), when extracting, then the readable
    article text is returned instead, same as if there were no ld+json at
    all."""
    html = f"""
    <html><head>
      <script type="application/ld+json">{json.dumps({"@type": "Organization", "name": "Blog"})}</script>
    </head><body>
      {(FIXTURES_DIR / "recipe_page.html").read_text(encoding="utf-8")}
    </body></html>
    """
    transport = _transport_returning(html)

    text = await fetch_and_extract_text(RECIPE_URL, transport=transport)

    assert "cenouras médias raladas" in text


async def test_given_any_page_when_fetching_then_the_user_agent_does_not_self_identify_as_a_bot() -> (
    None
):
    """Given any request, when fetching, then the User-Agent header looks
    like a real browser rather than announcing itself as a bot — several
    anti-bot / WAF rules block on the word "bot" alone regardless of the
    requester's actual origin or behavior."""
    html = (FIXTURES_DIR / "recipe_page.html").read_text(encoding="utf-8")
    seen_user_agent = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_user_agent
        seen_user_agent = request.headers.get("user-agent", "")
        return httpx.Response(200, text=html)

    await fetch_and_extract_text(RECIPE_URL, transport=httpx.MockTransport(handler))

    assert seen_user_agent is not None
    assert "bot" not in seen_user_agent.lower()


async def test_given_the_url_returns_an_error_status_when_fetching_then_the_failure_is_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Given the source URL responds with an HTTP error status, when
    fetching, then the failure is logged server-side (status code and URL)
    so it can be diagnosed later — the user only ever sees a generic
    translated message, so this is the only record of what actually
    happened."""
    transport = _transport_returning("forbidden", status_code=403)

    with caplog.at_level(logging.WARNING, logger="app.services.scraper"):
        with pytest.raises(UnreachableUrlError):
            await fetch_and_extract_text(RECIPE_URL, transport=transport)

    assert any(RECIPE_URL in record.message for record in caplog.records)
