"""Authentication endpoint: exchange a username and password for a token.

There is no sign-up route on purpose — accounts are created out of band by the
operator (see app/cli.py). This is the one public door into the API besides
/health.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.core.rate_limit import LOGIN_LIMIT, limiter
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.auth import CurrentUserResponse, LoginRequest, TokenResponse
from app.services.auth_service import authenticate_user, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit(LOGIN_LIMIT)
async def login(
    request: Request,
    credentials: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Return an access token when the username and password are correct.

    The `request` parameter is required by the rate limiter. On failure the
    message is deliberately the same for a wrong password and an unknown user,
    so it never reveals which usernames exist.
    """
    user = await authenticate_user(session, credentials.username, credentials.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválidos.",
        )
    return TokenResponse(access_token=create_access_token(user.username))


@router.get("/me", response_model=CurrentUserResponse)
async def read_current_user(
    user: User = Depends(get_current_user),
) -> CurrentUserResponse:
    """Return the signed-in account — lets the frontend check its stored token
    is still valid on startup without touching recipe data."""
    return CurrentUserResponse(username=user.username)
