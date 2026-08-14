"""SQLAlchemy model for an account that can sign in.

There is no open sign-up: accounts are created out of band by the operator
(see app/cli.py). The library of recipes is shared across all accounts, so a
user carries no ownership of recipes — it exists only to gate access to the
API behind a password.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    """An account allowed to use the API."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    # Never the password itself — only its Argon2 hash (see
    # app/services/auth_service.py). A leak of this column reveals no password.
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
