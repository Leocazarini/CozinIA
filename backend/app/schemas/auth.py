"""Pydantic schemas for authentication requests and responses."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Request body for POST /api/auth/login."""

    # Bounded so a login attempt can't ship a giant body; the values are only
    # ever compared, never rendered.
    username: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=1, max_length=1024)


class TokenResponse(BaseModel):
    """A freshly issued access token."""

    access_token: str
    token_type: str = "bearer"


class CurrentUserResponse(BaseModel):
    """The signed-in account, for the frontend to confirm its token is valid."""

    username: str
