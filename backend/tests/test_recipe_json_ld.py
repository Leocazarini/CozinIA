"""Specifications for extracting recipe data from schema.org/Recipe JSON-LD.

Most recipe sites embed a `<script type="application/ld+json">` block with
structured recipe data for Google's Rich Results — title, ingredients,
instructions and timings, already separated from surrounding boilerplate.
When present, this is far more reliable than reconstructing those same
fields from freeform readable text, so the scraper prefers it and only
falls back to text extraction when no usable block is found.
"""

import json

from app.services.recipe_json_ld import extract_recipe_text


def _html_with_ld_json(*blocks: object) -> str:
    scripts = "\n".join(
        f'<script type="application/ld+json">{json.dumps(block)}</script>' for block in blocks
    )
    return f"<html><head>{scripts}</head><body><p>página</p></body></html>"


def test_given_a_page_with_a_top_level_recipe_block_when_extracting_then_returns_its_fields() -> (
    None
):
    """Given a page with a single top-level schema.org/Recipe JSON-LD block
    (e.g. Dr. Oetker's markup), when extracting, then the returned text has
    the title, ingredients and timings from the structured data."""
    html = _html_with_ld_json(
        {
            "@context": "https://schema.org",
            "@type": "Recipe",
            "name": "Pudim de Leite Condensado",
            "recipeIngredient": [
                "1 lata de Leite Condensado (395g)",
                "3 unidades de Ovos",
            ],
            "recipeInstructions": [
                {"@type": "HowToStep", "text": "Bata tudo no liquidificador."},
                {"@type": "HowToStep", "text": "Asse em banho-maria por 60 minutos."},
            ],
            "prepTime": "PT20M",
            "cookTime": "PT60M",
            "totalTime": "PT1H20M",
            "recipeYield": "8 porções",
        }
    )

    text = extract_recipe_text(html)

    assert text is not None
    assert "Pudim de Leite Condensado" in text
    assert "1 lata de Leite Condensado (395g)" in text
    assert "3 unidades de Ovos" in text
    assert "Bata tudo no liquidificador." in text
    assert "Asse em banho-maria por 60 minutos." in text
    assert "Prep time: 20 minutes" in text
    assert "Cook time: 60 minutes" in text
    assert "Total time: 80 minutes" in text
    assert "8 porções" in text


def test_given_a_recipe_nested_inside_a_graph_when_extracting_then_it_is_still_found() -> None:
    """Given the Recipe object is nested inside an `@graph` array alongside
    other schema.org types (e.g. Nestlé's markup, which also emits Website
    and Organization blocks), when extracting, then the Recipe is still
    found and returned."""
    html = _html_with_ld_json(
        {
            "@context": "https://schema.org",
            "@graph": [
                {"@type": "WebSite", "name": "Receitas Nestlé"},
                {
                    "@type": "Recipe",
                    "name": "Pudim de Leite Moça",
                    "recipeIngredient": ["1 lata de leite condensado", "3 ovos"],
                    "recipeInstructions": "Derreta o açúcar.\nMisture tudo.\nAsse.",
                },
            ],
        }
    )

    text = extract_recipe_text(html)

    assert text is not None
    assert "Pudim de Leite Moça" in text
    assert "1 lata de leite condensado" in text
    assert "Derreta o açúcar." in text


def test_given_multiple_script_blocks_when_extracting_then_the_recipe_one_is_picked() -> None:
    """Given a page with several ld+json blocks (Organization, BreadcrumbList,
    Recipe), when extracting, then the non-Recipe blocks are ignored and the
    Recipe block is used."""
    html = _html_with_ld_json(
        {"@type": "Organization", "name": "Blog de Receitas"},
        {"@type": "BreadcrumbList", "itemListElement": []},
        {
            "@type": "Recipe",
            "name": "Bolo de Cenoura",
            "recipeIngredient": ["3 cenouras"],
            "recipeInstructions": ["Bata tudo.", "Leve ao forno."],
        },
    )

    text = extract_recipe_text(html)

    assert text is not None
    assert "Bolo de Cenoura" in text


def test_given_a_recipe_type_in_a_type_list_when_extracting_then_it_is_recognized() -> None:
    """Given the block's `@type` is a list (e.g. `["Recipe", "NewsArticle"]`)
    rather than a bare string, when extracting, then it is still recognized
    as a recipe."""
    html = _html_with_ld_json(
        {
            "@type": ["Recipe", "NewsArticle"],
            "name": "Torta de Limão",
            "recipeIngredient": ["1 lata de leite condensado"],
            "recipeInstructions": ["Misture e leve à geladeira."],
        }
    )

    text = extract_recipe_text(html)

    assert text is not None
    assert "Torta de Limão" in text


def test_given_recipe_instructions_grouped_in_sections_when_extracting_then_steps_are_flattened() -> (
    None
):
    """Given `recipeInstructions` uses `HowToSection` groups (e.g. "Calda"
    and "Recheio"), when extracting, then all nested steps are flattened
    into a single ordered list, in order."""
    html = _html_with_ld_json(
        {
            "@type": "Recipe",
            "name": "Pudim",
            "recipeIngredient": ["açúcar"],
            "recipeInstructions": [
                {
                    "@type": "HowToSection",
                    "name": "Calda",
                    "itemListElement": [
                        {"@type": "HowToStep", "text": "Derreta o açúcar."},
                    ],
                },
                {
                    "@type": "HowToSection",
                    "name": "Montagem",
                    "itemListElement": [
                        {"@type": "HowToStep", "text": "Despeje na forma."},
                        {"@type": "HowToStep", "text": "Leve ao forno."},
                    ],
                },
            ],
        }
    )

    text = extract_recipe_text(html)

    assert text is not None
    steps_order = [
        text.index("Derreta o açúcar."),
        text.index("Despeje na forma."),
        text.index("Leve ao forno."),
    ]
    assert steps_order == sorted(steps_order)


def test_given_no_ld_json_on_the_page_when_extracting_then_returns_none() -> None:
    """Given a page with no ld+json script tags at all, when extracting,
    then None is returned so the caller can fall back to another strategy."""
    html = "<html><body><article><p>Sem dados estruturados.</p></article></body></html>"

    assert extract_recipe_text(html) is None


def test_given_ld_json_present_but_no_recipe_type_when_extracting_then_returns_none() -> None:
    """Given the page has ld+json blocks but none of them are a Recipe (e.g.
    only Organization/WebSite), when extracting, then None is returned."""
    html = _html_with_ld_json(
        {"@type": "Organization", "name": "Blog de Receitas"},
        {"@type": "WebSite", "name": "Blog de Receitas"},
    )

    assert extract_recipe_text(html) is None


def test_given_a_recipe_block_with_no_ingredients_or_instructions_when_extracting_then_returns_none() -> (
    None
):
    """Given a Recipe block exists but has neither ingredients nor
    instructions (e.g. a stub/teaser card), when extracting, then it is
    treated as not usable and None is returned."""
    html = _html_with_ld_json({"@type": "Recipe", "name": "Pudim de Leite Condensado"})

    assert extract_recipe_text(html) is None


def test_given_malformed_json_in_a_script_block_when_extracting_then_it_is_skipped() -> None:
    """Given one ld+json script tag has invalid JSON, when extracting, then
    that block is skipped (not raised) and any other usable block is still
    found."""
    html = (
        "<html><head>"
        '<script type="application/ld+json">{not valid json</script>'
        '<script type="application/ld+json">'
        + json.dumps(
            {
                "@type": "Recipe",
                "name": "Bolo Simples",
                "recipeIngredient": ["farinha"],
                "recipeInstructions": ["Misture e asse."],
            }
        )
        + "</script></head><body></body></html>"
    )

    text = extract_recipe_text(html)

    assert text is not None
    assert "Bolo Simples" in text


def test_given_a_page_with_empty_html_when_extracting_then_returns_none() -> None:
    """Given an empty page, when extracting, then None is returned instead
    of raising."""
    assert extract_recipe_text("") is None


def test_given_instructions_with_embedded_html_when_extracting_then_tags_and_entities_are_stripped() -> (
    None
):
    """Given a step's text embeds raw HTML markup (a real pattern: some
    sites put `<br />`/`&nbsp;` inside `HowToStep.text` instead of plain
    text), when extracting, then the returned text has the step in plain
    text, with tags and entities gone rather than passed through verbatim."""
    html = _html_with_ld_json(
        {
            "@type": "Recipe",
            "name": "Pudim",
            "recipeIngredient": ["açúcar"],
            "recipeInstructions": [
                {
                    "@type": "HowToStep",
                    "text": "Derreta o açúcar.&nbsp;<br />Adicione a água cuidadosamente.",
                },
            ],
        }
    )

    text = extract_recipe_text(html)

    assert text is not None
    assert "Derreta o açúcar. Adicione a água cuidadosamente." in text
    assert "<br" not in text
    assert "&nbsp;" not in text


def test_given_an_image_object_when_extracting_then_its_url_is_included() -> None:
    """Given the recipe's `image` field is an ImageObject (rather than a
    plain string), when extracting, then its `url` is included in the
    returned text."""
    html = _html_with_ld_json(
        {
            "@type": "Recipe",
            "name": "Pudim",
            "recipeIngredient": ["leite condensado"],
            "recipeInstructions": ["Bata e asse."],
            "image": {"@type": "ImageObject", "url": "https://example.com/pudim.jpg"},
        }
    )

    text = extract_recipe_text(html)

    assert text is not None
    assert "https://example.com/pudim.jpg" in text
