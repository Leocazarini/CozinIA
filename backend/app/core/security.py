"""FastAPI dependency that gates protected routes behind a valid login token.

Applied once to the recipes router (see app/api/routes/recipes.py), so every
data endpoint requires a bearer token; /health and /api/auth/login stay public.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.auth_service import decode_access_token

# auto_error=False so a missing header yields our own 401 (with the
# WWW-Authenticate hint) rather than a 403 from the security scheme.
_bearer_scheme = HTTPBearer(auto_error=False)

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Autenticação necessária.",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """Resolve the account behind the request's bearer token, or raise 401.

    A token that verifies but names an account that no longer exists (deleted
    since the token was issued) is rejected too, so revoking access is as
    simple as removing the account.
    """
    if credentials is None:
        raise _UNAUTHENTICATED

    username = decode_access_token(credentials.credentials)
    if username is None:
        raise _UNAUTHENTICATED

    user = await UserRepository(session).get_by_username(username)
    if user is None:
        raise _UNAUTHENTICATED
    return user
