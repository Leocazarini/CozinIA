"""Shared pytest fixtures for the backend test suite."""

import asyncio
import os
import subprocess
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models.base import Base
from app.models.recipe import Recipe  # noqa: F401 - registers the table on Base.metadata

BACKEND_ROOT = Path(__file__).resolve().parent.parent


async def _delete_all_rows(database_url: str) -> None:
    """Delete every row from every table, self-contained (creates and
    disposes its own engine) so it is safe to call from a sync context via
    asyncio.run() without leaking a connection across event loops."""
    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            await connection.execute(table.delete())
    await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _migrated_test_database() -> None:
    """Apply the real Alembic migrations to the test database once per
    session (instead of a Base.metadata.create_all shortcut), so the schema
    under test always matches what a real deploy would run. Also clears any
    rows left behind by a previously interrupted run.
    """
    test_database_url = get_settings().test_database_url
    alembic_bin = Path(sys.executable).parent / "alembic"

    subprocess.run(
        [str(alembic_bin), "upgrade", "head"],
        cwd=BACKEND_ROOT,
        env={**os.environ, "DATABASE_URL": test_database_url},
        check=True,
    )
    asyncio.run(_delete_all_rows(test_database_url))


@pytest_asyncio.fixture
async def db_session(_migrated_test_database: None) -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session backed by the real test database.

    A fresh engine is created for each test (rather than shared across the
    session) so its connections stay bound to the event loop pytest-asyncio
    creates for that test — sharing one across tests causes asyncpg
    "another operation is in progress" errors once the loop is recycled.
    """
    test_database_url = get_settings().test_database_url
    engine = create_async_engine(test_database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    await _delete_all_rows(test_database_url)
    await engine.dispose()
