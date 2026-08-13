"""Specifications for RecipeService, which orchestrates source reading, AI
extraction, and persistence for the recipe creation flow.

A recipe can come from a link (scraped), from uploaded photos (transcribed),
or from a video link (read, then narration and description merged); all three
converge on the same extraction and persistence, and a saved recipe is the
same kind of thing whichever way it arrived.

Reading and AI extraction are stubbed here — they have their own test
suites (test_scraper.py, test_image_transcriber.py, test_video_source.py,
test_video_transcriber.py, test_ai_extractor.py); this file specifies the
orchestration itself, run against the real test database.
"""

from collections.abc import Sequence

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.recipe import IngredientExtraction, RecipeExtraction, StepExtraction
from app.services.ai_extractor import AIRequestError, NotARecipeError
from app.services.image_transcriber import UnreadableImageError
from app.services.recipe_service import RecipeService
from app.services.recipe_translator import TranslationResult
from app.services.scraper import UnreachableUrlError
from app.services.video_source import (
    NoVideoTextError,
    SpeechSource,
    VideoMaterial,
    VideoUnavailableError,
)

FAKE_MATERIAL = VideoMaterial(
    title="Bolo de cenoura da vovó",
    uploader="Cozinha da Vovó",
    description="3 cenouras médias, 3 ovos, 2 xícaras de açúcar",
    caption_transcript="bate tudo no liquidificador e leva ao forno",
    speech_source=SpeechSource.AUTOMATIC_CAPTIONS,
    audio=None,
)

FAKE_EXTRACTION = RecipeExtraction(
    title="Bolo de cenoura",
    servings=8,
    prep_time_minutes=15,
    ingredients=[IngredientExtraction(name="cenoura", quantity="3", unit="unidades")],
    steps=[StepExtraction(order=1, text="Bata tudo e leve ao forno.")],
)

# What a (stubbed) translation of FAKE_EXTRACTION would look like — a
# different title is enough to prove the *translated* recipe is what gets
# persisted, not the one AI extraction returned.
TRANSLATED_EXTRACTION = RecipeExtraction(
    title="Bolo de cenoura (traduzido)",
    servings=8,
    prep_time_minutes=15,
    ingredients=[IngredientExtraction(name="cenoura", quantity="3", unit="unidades")],
    steps=[StepExtraction(order=1, text="Bata tudo e leve ao forno.")],
)


async def _stub_scrape(url: str) -> str:
    return "texto extraído da página"


async def _stub_extract(text: str) -> RecipeExtraction:
    return FAKE_EXTRACTION


async def _stub_translate(extraction: RecipeExtraction) -> TranslationResult:
    return TranslationResult(extraction=TRANSLATED_EXTRACTION, source_language="en")


async def _stub_transcribe(images: Sequence[bytes]) -> str:
    return "texto transcrito das fotos"


async def _stub_read_video(url: str) -> VideoMaterial:
    return FAKE_MATERIAL


async def _stub_transcribe_video(material: VideoMaterial) -> str:
    return "receita montada a partir do vídeo"


async def test_given_a_url_when_creating_a_recipe_then_it_is_scraped_extracted_and_persisted(
    db_session: AsyncSession,
) -> None:
    """Given a URL, when creating a recipe from it, then the page is
    scraped, the text is sent for AI extraction, and the result is
    persisted with the source URL, extracted fields, and AI metadata."""
    service = RecipeService(db_session, scrape=_stub_scrape, extract=_stub_extract)

    recipe = await service.create_from_url("https://example.com/receita")

    assert recipe.id is not None
    assert recipe.source_url == "https://example.com/receita"
    assert recipe.title == "Bolo de cenoura"
    assert recipe.servings == 8
    assert recipe.ingredients[0]["name"] == "cenoura"
    assert recipe.steps[0]["text"] == "Bata tudo e leve ao forno."
    assert recipe.raw_extracted_text == "texto extraído da página"
    assert recipe.source_type == "link"
    assert recipe.ai_provider == "openrouter"
    assert recipe.ai_model


async def test_given_photos_of_a_recipe_when_creating_a_recipe_then_they_are_transcribed_extracted_and_persisted(
    db_session: AsyncSession,
) -> None:
    """Given photos of a recipe, when creating a recipe from them, then they
    are transcribed, that text goes through the same AI extraction the link
    flow uses, and the result is persisted with no source URL — the photos
    themselves are not kept, so the transcription is what remains of them."""
    service = RecipeService(db_session, transcribe=_stub_transcribe, extract=_stub_extract)

    recipe = await service.create_from_images([b"foto-pagina-1", b"foto-pagina-2"])

    assert recipe.id is not None
    assert recipe.source_url is None
    assert recipe.source_type == "image"
    assert recipe.title == "Bolo de cenoura"
    assert recipe.ingredients[0]["name"] == "cenoura"
    assert recipe.steps[0]["text"] == "Bata tudo e leve ao forno."
    assert recipe.raw_extracted_text == "texto transcrito das fotos"
    assert recipe.ai_provider == "openrouter"
    assert recipe.ai_model


async def test_given_a_video_link_when_creating_a_recipe_then_it_is_read_merged_extracted_and_persisted(
    db_session: AsyncSession,
) -> None:
    """Given a video link, when creating a recipe from it, then the video is
    read, its description and narration are merged into one document, that
    document goes through the same AI extraction the other two doors use, and
    the result is persisted with the video's URL.

    What is kept in `raw_extracted_text` is the merged document, not the raw
    material: it is the readable record of what the recipe was built from.
    """
    service = RecipeService(
        db_session,
        read_video=_stub_read_video,
        transcribe_video=_stub_transcribe_video,
        extract=_stub_extract,
    )

    recipe = await service.create_from_video_url("https://www.youtube.com/watch?v=abc123")

    assert recipe.id is not None
    assert recipe.source_url == "https://www.youtube.com/watch?v=abc123"
    assert recipe.source_type == "video"
    assert recipe.title == "Bolo de cenoura"
    assert recipe.ingredients[0]["name"] == "cenoura"
    assert recipe.steps[0]["text"] == "Bata tudo e leve ao forno."
    assert recipe.raw_extracted_text == "receita montada a partir do vídeo"
    assert recipe.ai_provider == "openrouter"
    assert recipe.ai_model


async def test_given_a_portuguese_extraction_when_creating_a_recipe_from_a_url_then_it_is_persisted_untranslated(
    db_session: AsyncSession,
) -> None:
    """Given the extracted recipe is already in Portuguese, when creating a
    recipe from a link, then the real (unstubbed) translation step runs,
    detects it needs no translation, and the recipe is persisted exactly as
    extracted, with no source_language recorded."""
    service = RecipeService(db_session, scrape=_stub_scrape, extract=_stub_extract)

    recipe = await service.create_from_url("https://example.com/receita")

    assert recipe.title == "Bolo de cenoura"
    assert recipe.source_language is None


async def test_given_a_foreign_language_extraction_when_creating_a_recipe_from_a_url_then_the_translation_is_persisted(
    db_session: AsyncSession,
) -> None:
    """Given the extracted recipe is in another language, when creating a
    recipe from a link, then the translated recipe — not the one AI
    extraction returned — is what gets persisted, tagged with the language
    it was translated from."""
    service = RecipeService(
        db_session, scrape=_stub_scrape, extract=_stub_extract, translate=_stub_translate
    )

    recipe = await service.create_from_url("https://example.com/receita")

    assert recipe.title == "Bolo de cenoura (traduzido)"
    assert recipe.source_language == "en"


async def test_given_a_foreign_language_extraction_when_creating_a_recipe_from_images_then_the_translation_is_persisted(
    db_session: AsyncSession,
) -> None:
    """Given photos whose extracted recipe is in another language, when
    creating a recipe from them, then the translated recipe is persisted —
    the same translation step the link door uses, since both converge on
    the same extraction."""
    service = RecipeService(
        db_session, transcribe=_stub_transcribe, extract=_stub_extract, translate=_stub_translate
    )

    recipe = await service.create_from_images([b"foto-pagina-1"])

    assert recipe.title == "Bolo de cenoura (traduzido)"
    assert recipe.source_language == "en"


async def test_given_a_foreign_language_extraction_when_creating_a_recipe_from_a_video_then_the_translation_is_persisted(
    db_session: AsyncSession,
) -> None:
    """Given a video whose extracted recipe is in another language, when
    creating a recipe from it, then the translated recipe is persisted —
    the same translation step the other two doors use."""
    service = RecipeService(
        db_session,
        read_video=_stub_read_video,
        transcribe_video=_stub_transcribe_video,
        extract=_stub_extract,
        translate=_stub_translate,
    )

    recipe = await service.create_from_video_url("https://www.youtube.com/watch?v=abc123")

    assert recipe.title == "Bolo de cenoura (traduzido)"
    assert recipe.source_language == "en"


async def test_given_the_video_cannot_be_read_when_creating_a_recipe_then_the_error_propagates(
    db_session: AsyncSession,
) -> None:
    """Given a video that is private, deleted or blocked, when creating a
    recipe, then VideoUnavailableError propagates unchanged and nothing is
    persisted — the API layer is responsible for translating it."""

    async def unavailable_read(url: str) -> VideoMaterial:
        raise VideoUnavailableError("boom")

    service = RecipeService(
        db_session,
        read_video=unavailable_read,
        transcribe_video=_stub_transcribe_video,
        extract=_stub_extract,
    )

    with pytest.raises(VideoUnavailableError):
        await service.create_from_video_url("https://www.youtube.com/watch?v=privado")


async def test_given_the_video_has_nothing_to_read_when_creating_a_recipe_then_the_error_propagates(
    db_session: AsyncSession,
) -> None:
    """Given a video with no narration and nothing written, when creating a
    recipe, then NoVideoTextError propagates unchanged and nothing is
    persisted."""

    async def empty_transcribe(material: VideoMaterial) -> str:
        raise NoVideoTextError("boom")

    service = RecipeService(
        db_session,
        read_video=_stub_read_video,
        transcribe_video=empty_transcribe,
        extract=_stub_extract,
    )

    with pytest.raises(NoVideoTextError):
        await service.create_from_video_url("https://www.instagram.com/reel/xyz")


async def test_given_the_video_is_not_a_recipe_when_creating_a_recipe_then_the_error_propagates(
    db_session: AsyncSession,
) -> None:
    """Given a video that reads fine but describes no recipe, when creating a
    recipe, then NotARecipeError propagates unchanged — the same rejection the
    other two doors get, since all three share the extraction step."""

    async def not_a_recipe_extract(text: str) -> RecipeExtraction:
        raise NotARecipeError("o vídeo não tem ingredientes nem modo de preparo")

    service = RecipeService(
        db_session,
        read_video=_stub_read_video,
        transcribe_video=_stub_transcribe_video,
        extract=not_a_recipe_extract,
    )

    with pytest.raises(NotARecipeError):
        await service.create_from_video_url("https://www.youtube.com/watch?v=unboxing")


async def test_given_the_photos_cannot_be_read_when_creating_a_recipe_then_the_error_propagates(
    db_session: AsyncSession,
) -> None:
    """Given the vision model gets no usable text out of the photos, when
    creating a recipe, then UnreadableImageError propagates unchanged and
    nothing is persisted."""

    async def unreadable_transcribe(images: Sequence[bytes]) -> str:
        raise UnreadableImageError("boom")

    service = RecipeService(db_session, transcribe=unreadable_transcribe, extract=_stub_extract)

    with pytest.raises(UnreadableImageError):
        await service.create_from_images([b"foto-borrada"])


async def test_given_the_photos_are_not_a_recipe_when_creating_a_recipe_then_the_error_propagates(
    db_session: AsyncSession,
) -> None:
    """Given the photos read fine but describe no recipe, when creating a
    recipe, then NotARecipeError propagates unchanged — the same rejection
    the link flow gets, since both share the extraction step."""

    async def not_a_recipe_extract(text: str) -> RecipeExtraction:
        raise NotARecipeError("a foto não tem ingredientes nem modo de preparo")

    service = RecipeService(db_session, transcribe=_stub_transcribe, extract=not_a_recipe_extract)

    with pytest.raises(NotARecipeError):
        await service.create_from_images([b"foto-de-um-cardapio"])


async def test_given_the_source_page_is_unreachable_when_creating_a_recipe_then_the_error_propagates(
    db_session: AsyncSession,
) -> None:
    """Given the scraper cannot reach the source URL, when creating a
    recipe, then UnreachableUrlError propagates unchanged — the API layer
    is responsible for translating it into a user-facing response."""

    async def failing_scrape(url: str) -> str:
        raise UnreachableUrlError("boom")

    service = RecipeService(db_session, scrape=failing_scrape, extract=_stub_extract)

    with pytest.raises(UnreachableUrlError):
        await service.create_from_url("https://example.com/receita")


async def test_given_the_ai_request_fails_when_creating_a_recipe_then_the_error_propagates(
    db_session: AsyncSession,
) -> None:
    """Given the AI extraction request fails, when creating a recipe, then
    AIRequestError propagates unchanged — the API layer is responsible for
    translating it into a user-facing response."""

    async def failing_extract(text: str) -> RecipeExtraction:
        raise AIRequestError("boom")

    service = RecipeService(db_session, scrape=_stub_scrape, extract=failing_extract)

    with pytest.raises(AIRequestError):
        await service.create_from_url("https://example.com/receita")


async def test_given_the_source_is_not_a_recipe_when_creating_a_recipe_then_the_error_propagates(
    db_session: AsyncSession,
) -> None:
    """Given the AI determines the source text isn't a recipe, when
    creating a recipe, then NotARecipeError propagates unchanged and
    nothing is persisted — the API layer is responsible for translating it
    into a user-facing response."""

    async def not_a_recipe_extract(text: str) -> RecipeExtraction:
        raise NotARecipeError("a página não tem ingredientes nem modo de preparo")

    service = RecipeService(db_session, scrape=_stub_scrape, extract=not_a_recipe_extract)

    with pytest.raises(NotARecipeError):
        await service.create_from_url("https://example.com/nao-e-receita")
