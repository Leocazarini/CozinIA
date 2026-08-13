"""Maps domain exceptions raised deep in the service layer to HTTP
responses with user-facing (Portuguese) messages.

Recipe-not-found is handled inline in the route (it's a routine, expected
outcome); this module covers everything a recipe submission can fail on —
a rejected photo upload, a video link that can't be read, and the ways the
scrape/transcribe/AI pipeline can fail on external systems, bubbling up from
nested service calls.

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
from app.services.video_source import (
    MAX_VIDEO_DURATION_MINUTES,
    NotASingleVideoError,
    NoVideoTextError,
    UnsupportedVideoUrlError,
    VideoAccessBlockedError,
    VideoTooLongError,
    VideoUnavailableError,
)
from app.services.video_transcriber import UnreadableVideoError

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
    UnsupportedVideoUrlError: (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "Não reconhecemos um vídeo nesse link.",
    ),
    NotASingleVideoError: (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "Esse link é de um canal, perfil ou playlist. Envie o link de um vídeo específico.",
    ),
    VideoUnavailableError: (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "Não foi possível acessar esse vídeo. Ele pode ser privado, ter sido removido, "
        "ou exigir login.",
    ),
    # A 503 and not a 422: it is our server being refused, not the user's link
    # being wrong, and telling them their perfectly good link is unavailable
    # would send them off debugging the wrong thing. Registered alongside its
    # parent VideoUnavailableError on purpose — Starlette matches on the
    # exception's MRO, so the subclass entry wins whenever it applies.
    VideoAccessBlockedError: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "A plataforma do vídeo está bloqueando as requisições do nosso servidor. "
        "Tente novamente mais tarde.",
    ),
    VideoTooLongError: (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        f"Vídeo muito longo. O limite é {MAX_VIDEO_DURATION_MINUTES} minutos.",
    ),
    NoVideoTextError: (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "Não conseguimos ouvir nem ler nenhuma receita nesse vídeo. Tente um vídeo com "
        "legendas, com narração, ou com a receita escrita na descrição.",
    ),
    UnreadableVideoError: (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "Não conseguimos montar a receita a partir desse vídeo. Tente um vídeo em que os "
        "ingredientes e o modo de preparo sejam ditos ou escritos.",
    ),
    # Deliberately source-neutral: the same rejection has to read correctly
    # whether the user pasted a link, uploaded a photo, or sent a video.
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
