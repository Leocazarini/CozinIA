"""Data access layer for user accounts."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """Encapsulates all database access for the User aggregate."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_username(self, username: str) -> User | None:
        """Return the account with the given username, or None if there is none."""
        statement = select(User).where(User.username == username)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        """Persist a new account and return it with generated fields populated."""
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user
