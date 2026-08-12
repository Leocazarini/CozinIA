"""Extracts recipe data from schema.org/Recipe JSON-LD embedded in a page.

Recipe sites almost universally embed a `<script type="application/ld+json">`
block describing the recipe (title, ingredients, instructions, timings) so
that Google can show it as a Rich Result. That data is already separated
from surrounding navigation/ads/related-posts boilerplate, which makes it a
far more reliable source for the AI extractor than reconstructing the same
fields from freeform readable text — so the scraper tries this first.
"""

import html
import json
import re
from collections.abc import Iterator

import lxml.etree
import lxml.html

_ISO8601_DURATION_RE = re.compile(
    r"^P(?:(?P<days>\d+)D)?"
    r"(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _clean_text(value: str) -> str:
    """Some sites put raw HTML markup (`<br />`, `&nbsp;`) inside otherwise
    plain-text JSON-LD fields like a step's `text`. Strip tags and unescape
    entities so the AI extractor sees plain text either way."""
    without_tags = _HTML_TAG_RE.sub(" ", value)
    unescaped = html.unescape(without_tags)
    return re.sub(r"\s+", " ", unescaped).strip()


def extract_recipe_text(html: str) -> str | None:
    """Look for a schema.org/Recipe block in `html`'s JSON-LD and, if one is
    found with enough substance to be useful, render it as clean, labeled
    plain text.

    Returns None when no usable Recipe block is present (no ld+json at all,
    none of it a Recipe, or a Recipe with neither ingredients nor
    instructions), so the caller can fall back to another extraction
    strategy.
    """
    for block in _parsed_json_ld_blocks(html):
        for node in _iter_candidate_nodes(block):
            if _is_recipe(node) and _is_usable(node):
                return _render(node)
    return None


def _parsed_json_ld_blocks(html: str) -> Iterator[object]:
    try:
        tree = lxml.html.fromstring(html)
    except lxml.etree.ParserError:
        return
    for script in tree.xpath('//script[@type="application/ld+json"]'):
        raw = script.text_content()
        if not raw or not raw.strip():
            continue
        try:
            yield json.loads(raw)
        except json.JSONDecodeError:
            continue


def _iter_candidate_nodes(node: object) -> Iterator[dict]:
    """Walk a parsed ld+json value, yielding every dict that could plausibly
    carry an `@type`, including ones nested under `@graph` (a common wrapper
    when a page emits several schema.org entities in one block)."""
    if isinstance(node, dict):
        yield node
        graph = node.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                yield from _iter_candidate_nodes(item)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_candidate_nodes(item)


def _is_recipe(node: dict) -> bool:
    node_type = node.get("@type")
    if isinstance(node_type, str):
        return node_type == "Recipe"
    if isinstance(node_type, list):
        return "Recipe" in node_type
    return False


def _is_usable(recipe: dict) -> bool:
    name = recipe.get("name")
    if not isinstance(name, str) or not name.strip():
        return False
    return bool(_ingredient_lines(recipe)) or bool(_instruction_lines(recipe))


def _render(recipe: dict) -> str:
    lines = [f"Title: {_clean_text(recipe['name'])}"]

    description = recipe.get("description")
    if isinstance(description, str) and description.strip():
        lines.append(f"Description: {_clean_text(description)}")

    image_url = _image_url(recipe)
    if image_url:
        lines.append(f"Image: {image_url}")

    yield_text = _yield_text(recipe)
    if yield_text:
        lines.append(f"Servings: {yield_text}")

    for label, field in (
        ("Prep time", "prepTime"),
        ("Cook time", "cookTime"),
        ("Total time", "totalTime"),
    ):
        minutes = _duration_to_minutes(recipe.get(field))
        if minutes is not None:
            lines.append(f"{label}: {minutes} minutes")

    ingredient_lines = _ingredient_lines(recipe)
    if ingredient_lines:
        lines.append("Ingredients:")
        lines.extend(f"- {line}" for line in ingredient_lines)

    instruction_lines = _instruction_lines(recipe)
    if instruction_lines:
        lines.append("Instructions:")
        lines.extend(f"{i}. {line}" for i, line in enumerate(instruction_lines, start=1))

    keywords = recipe.get("keywords")
    if isinstance(keywords, str) and keywords.strip():
        lines.append(f"Keywords: {_clean_text(keywords)}")

    return "\n".join(lines)


def _ingredient_lines(recipe: dict) -> list[str]:
    ingredients = recipe.get("recipeIngredient")
    if not isinstance(ingredients, list):
        return []
    return [_clean_text(str(item)) for item in ingredients if str(item).strip()]


def _instruction_lines(recipe: dict) -> list[str]:
    instructions = recipe.get("recipeInstructions")
    if isinstance(instructions, str):
        return [_clean_text(line) for line in instructions.splitlines() if line.strip()]
    if isinstance(instructions, list):
        lines: list[str] = []
        for item in instructions:
            lines.extend(_flatten_instruction_item(item))
        return lines
    return []


def _flatten_instruction_item(item: object) -> list[str]:
    """A `recipeInstructions` entry is either a plain string, a `HowToStep`
    (has `text`), or a `HowToSection` grouping nested steps under
    `itemListElement` (e.g. "Calda" / "Recheio"). Sections are flattened
    into the same ordered list rather than kept as a separate structure —
    the AI extractor only needs steps in order, not their grouping."""
    if isinstance(item, str):
        return [_clean_text(item)] if item.strip() else []
    if isinstance(item, dict):
        if item.get("@type") == "HowToSection":
            nested = item.get("itemListElement")
            lines: list[str] = []
            for sub in nested if isinstance(nested, list) else []:
                lines.extend(_flatten_instruction_item(sub))
            return lines
        text = item.get("text") or item.get("name")
        return [_clean_text(str(text))] if text and str(text).strip() else []
    return []


def _image_url(recipe: dict) -> str | None:
    image = recipe.get("image")
    if isinstance(image, str):
        return image.strip() or None
    if isinstance(image, dict):
        url = image.get("url")
        return url.strip() if isinstance(url, str) and url.strip() else None
    if isinstance(image, list) and image:
        return _image_url({"image": image[0]})
    return None


def _yield_text(recipe: dict) -> str | None:
    value = recipe.get("recipeYield")
    if isinstance(value, list) and value:
        value = value[0]
    if isinstance(value, str | int) and str(value).strip():
        return str(value).strip()
    return None


def _duration_to_minutes(value: object) -> int | None:
    """Parse an ISO 8601 duration (e.g. "PT1H20M") into whole minutes.
    Returns None for anything that isn't a recognizable duration, so a
    malformed value is silently omitted rather than breaking extraction."""
    if not isinstance(value, str):
        return None
    match = _ISO8601_DURATION_RE.match(value.strip())
    if not match:
        return None
    parts = {key: int(group) for key, group in match.groupdict(default="0").items()}
    if not any(parts.values()):
        return None
    return parts["days"] * 24 * 60 + parts["hours"] * 60 + parts["minutes"] + parts["seconds"] // 60
