"""Health check route, used by Docker Compose to gate dependent services."""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import check_database_connection, get_db_session
from app.schemas.health import HealthStatus

router = APIRouter()


async def get_is_database_reachable(
    session: AsyncSession = Depends(get_db_session),
) -> bool:
    """FastAPI dependency wrapping the database connectivity check.

    Kept separate from the route so tests can override it directly,
    without needing a real database connection.
    """
    return await check_database_connection(session)


@router.get("/health", response_model=HealthStatus)
async def get_health(
    response: Response,
    database_reachable: bool = Depends(get_is_database_reachable),
) -> HealthStatus:
    """Report whether the backend can reach the database."""
    if not database_reachable:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthStatus(status="error")
    return HealthStatus(status="ok")
