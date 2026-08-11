"""Response schema for the health endpoint."""

from pydantic import BaseModel


class HealthStatus(BaseModel):
    """Reports whether the backend is operational."""

    status: str
