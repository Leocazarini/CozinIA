"""Maps domain exceptions raised deep in the service layer to HTTP
responses with user-facing (Portuguese) messages.

Recipe-not-found is handled inline in the route (it's a routine, expected
outcome); this module covers the ways the scrape/AI pipeline can fail —
unexpected failures from external systems that bubble up from nested
service calls.
"""

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.services.ai_extractor import AIRequestError, MalformedAIResponseError, NotARecipeError
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
    NotARecipeError: (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "Esse link não parece ser de uma receita — não encontramos ingredientes "
        "nem modo de preparo na página.",
    ),
    AIRequestError: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "O serviço de extração por IA está indisponível no momento. Tente novamente em instantes.",
    ),
    MalformedAIResponseError: (
        status.HTTP_502_BAD_GATEWAY,
        "Não foi possível interpretar a receita extraída desse link. "
        "Tente novamente ou use outro link.",
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
