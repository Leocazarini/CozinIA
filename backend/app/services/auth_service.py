"""Password hashing and login-token issuing/verification.

Passwords are hashed with Argon2 (via pwdlib): the stored column is never the
password, only a hash that is expensive to reverse. Sessions are stateless
JWTs signed with the app's JWT_SECRET — the server keeps no session table; a
token is trusted because it verifies against the secret and has not expired.
"""

import logging
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.user import User
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

_password_hash = PasswordHash.recommended()

# A precomputed hash to verify against when the username is unknown, so a login
# attempt takes about the same time whether or not the account exists — closing
# the timing side channel that would otherwise reveal which usernames are real.
_DUMMY_HASH = _password_hash.hash("dummy-password-for-constant-time-compare")


def hash_password(password: str) -> str:
    """Return an Argon2 hash of `password`, safe to store."""
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return True if `password` matches the stored `password_hash`."""
    return _password_hash.verify(password, password_hash)


def create_access_token(subject: str) -> str:
    """Issue a signed token identifying `subject` (a username), expiring per settings."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    """Return the subject (username) of a valid token, or None if it is
    invalid, expired, or tampered with."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
    subject = payload.get("sub")
    return subject if isinstance(subject, str) else None


async def authenticate_user(session: AsyncSession, username: str, password: str) -> User | None:
    """Return the account for `username` when `password` is correct, else None.

    Always performs a password verification — even when the username is
    unknown — so the response time does not reveal whether the account exists.
    """
    user = await UserRepository(session).get_by_username(username)
    if user is None:
        verify_password(password, _DUMMY_HASH)
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
