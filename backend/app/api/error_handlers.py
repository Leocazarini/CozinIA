"""Maps domain exceptions raised deep in the service layer to HTTP
responses with user-facing (Portuguese) messages.

Recipe-not-found is handled inline in the route (it's a routine, expected
outcome); this module covers everything a recipe submission can fail on —
a rejected photo upload, and the ways the scrape/transcribe/AI pipeline can
fail on external systems, bubbling up from nested service calls.

Keeping every one of these strings here (rather than at each raise site) is
what makes the code-in-English / user-in-Portuguese split hold: this is the
one file where the app speaks to the user.
"""

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.services.ai_extractor import AIRequestError, MalformedAIResponseError, NotARecipeError
from app.services.image_intake import (
    MAX_IMAGES,
    ImageTooLargeError,
    NoImagesProvidedError,
    TooManyImagesError,
    UnsupportedImageTypeError,
)
from app.services.image_transcriber import UnreadableImageError
from app.services.scraper import NoExtractableContentError, UnreachableUrlError

_ERROR_RESPONSES: dict[type[Exception], tuple[int, str]] = {
    UnreachableUrlError: (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "Não foi possível acessar o link informado.",
    ),
    NoExtractableContentError: (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "Não encontramos uma receita no conteúdo dessa página.",
    ),
    NoImagesProvidedError: (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "Envie pelo menos uma imagem da receita.",
    ),
    TooManyImagesError: (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        f"Envie no máximo {MAX_IMAGES} imagens por receita.",
    ),
    UnsupportedImageTypeError: (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "Formato de imagem não suportado. Use JPG, PNG ou WebP.",
    ),
    ImageTooLargeError: (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "Imagem muito grande. O limite é 10 MB por foto.",
    ),
    UnreadableImageError: (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "Não conseguimos ler o texto dessa imagem. Tente uma foto mais nítida, "
        "com a receita bem enquadrada.",
    ),
    # Deliberately source-neutral: the same rejection has to read correctly
    # whether the user pasted a link or uploaded a photo.
    NotARecipeError: (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "Não encontramos uma receita aqui — não identificamos ingredientes "
        "nem modo de preparo.",
    ),
    AIRequestError: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "O serviço de extração por IA está indisponível no momento. Tente novamente em instantes.",
    ),
    MalformedAIResponseError: (
        status.HTTP_502_BAD_GATEWAY,
        "Não foi possível interpretar a receita extraída. Tente novamente.",
    ),
}


def register_error_handlers(app: FastAPI) -> None:
    """Register a JSON error response for each known domain exception."""
    for exception_type, (status_code, message) in _ERROR_RESPONSES.items():
        app.add_exception_handler(exception_type, _handler_for(status_code, message))


def _handler_for(
    status_code: int, message: str
) -> Callable[[Request, Exception], Coroutine[Any, Any, JSONResponse]]:
    async def handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": message})

    return handler
